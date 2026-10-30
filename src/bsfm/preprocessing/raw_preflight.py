"""Read-only, bounded-memory H5AD audit for the frozen 19-section contract.

No normalization is performed. Metadata and per-cell summaries fit in memory;
expression values are visited in bounded blocks. Only aggregate reports leave
this module. Exclusion row numbers identify cells in the hashed source locally.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import sys
from pathlib import Path

import h5py
import numpy as np


SCHEMA = "bsfm.raw-preflight.v1"
REGISTRY = Path(__file__).with_name("sections.json")
TYPE_LABELS = {"MIC": "Mic", "AST": "AST", "OGC": "OGC"}
QUANTILES = {"min": 0, "q01": .01, "q05": .05, "q25": .25,
             "median": .5, "q75": .75, "q95": .95, "q99": .99, "max": 1}
REASONS = ("nonfinite_count", "negative_count", "noninteger_count",
           "unsafe_total", "invalid_spatial", "missing_cell_type",
           "missing_section_metadata", "unregistered_section", "zero_total")


class ContractError(ValueError):
    """Dataset-wide schema or identity failure; no depth may be accepted."""


def require(condition, message):
    if not condition:
        raise ContractError(message)


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ordered_hash(strings):
    """SHA-256 of ordered UTF-8 strings, each prefixed by uint64-LE byte length."""
    digest = hashlib.sha256()
    for value in strings:
        encoded = value.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "little"))
        digest.update(encoded)
    return digest.hexdigest()


def text(value):
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


def strings(node):
    """Decode H5AD string arrays or categorical columns (-1 means missing)."""
    if isinstance(node, h5py.Dataset):
        require(node.ndim == 1 and h5py.check_string_dtype(node.dtype) is not None,
                f"{node.name}: expected one-dimensional string array")
        return node.asstr()[:]
    require(text(node.attrs.get("encoding-type", "")) == "categorical",
            f"{node.name}: unsupported metadata encoding")
    require("categories" in node and "codes" in node, f"{node.name}: incomplete categorical")
    categories = strings(node["categories"])
    codes = node["codes"][:]
    require(codes.ndim == 1 and codes.dtype.kind in "iu", f"{node.name}: invalid codes")
    require(len(set(categories)) == len(categories), f"{node.name}: duplicate categories")
    require(np.all((codes >= -1) & (codes < len(categories))), f"{node.name}: code out of range")
    result = np.full(len(codes), "", dtype=object)
    present = codes >= 0
    result[present] = categories[codes[present]]
    return result


def axis_ids(group):
    key = text(group.attrs.get("_index", "_index"))
    require(key in group, f"{group.name}: missing identifier index {key}")
    values = strings(group[key])
    require(all(v.strip() for v in values), f"{group.name}: empty identifiers")
    require(len(set(values)) == len(values), f"{group.name}: duplicate identifiers")
    return values, f"{group.name}/{key}"


def numeric_dtype(dtype, name):
    require(dtype.kind in "iuf", f"{name}: expected real numeric storage")


def count_totals(node, shape, chunk_rows):
    """Visit dense, CSR or CSC counts, keeping only totals and invalid-row masks.

    Sparse entries must have strictly increasing indices per compressed vector:
    reject ambiguous duplicate/unsorted storage rather than repairing it silently.
    Each entry slice is bounded by chunk_rows * n_genes, including long CSC columns.
    Sum validated entries in uint64 (300 * 2**53 fits); totals above 2**53
    are excluded before float64 quantiles, avoiding silent precision loss.
    """
    n, g = shape
    totals = np.zeros(n, dtype=np.uint64)
    bad = {k: np.zeros(n, dtype=bool) for k in REASONS[:4]}
    invalid_values = {k: 0 for k in REASONS[:3]}

    def consume(values, rows):
        finite = np.isfinite(values)
        flags = {"nonfinite_count": ~finite,
                 "negative_count": finite & (values < 0),
                 "noninteger_count": finite & (values != np.floor(values))}
        valid = np.ones(values.shape, dtype=bool)
        for name, flag in flags.items():
            invalid_values[name] += int(flag.sum())
            bad[name][rows[flag]] = True
            valid &= ~flag
        too_large = valid & (values > 2**53)
        bad["unsafe_total"][rows[too_large]] = True
        valid &= ~too_large
        np.add.at(totals, rows[valid], values[valid].astype(np.uint64))

    if isinstance(node, h5py.Dataset):
        require(node.shape == shape, "layers/RNA shape does not match cell/gene axes")
        numeric_dtype(node.dtype, node.name)
        for start in range(0, n, chunk_rows):
            block = node[start:start + chunk_rows, :]
            rows = np.repeat(np.arange(start, start + len(block)), g)
            consume(block.reshape(-1), rows)
        storage = "dense"
        dtype = str(node.dtype)
    else:
        storage = text(node.attrs.get("encoding-type", ""))
        require(storage in ("csr_matrix", "csc_matrix"), "Unsupported sparse RNA encoding")
        require(tuple(node.attrs.get("shape", ())) == shape, "Sparse RNA shape mismatch")
        require(all(k in node for k in ("data", "indices", "indptr")), "Incomplete sparse RNA")
        data, indices, ptr = (node[k] for k in ("data", "indices", "indptr"))
        require(all(x.ndim == 1 for x in (data, indices, ptr)), "Sparse arrays must be 1D")
        numeric_dtype(data.dtype, data.name)
        require(indices.dtype.kind in "iu" and ptr.dtype.kind in "iu", "Sparse indices must be integers")
        major, minor = (n, g) if storage == "csr_matrix" else (g, n)
        require(len(ptr) == major + 1 and len(indices) == len(data), "Sparse lengths inconsistent")
        pointers = ptr[:]
        require(pointers[0] == 0 and pointers[-1] == len(data)
                and np.all(pointers[1:] >= pointers[:-1])
                and np.all(pointers <= len(data)), "Malformed sparse indptr")
        # For CSR, batch whole rows. For CSC, batch columns (only 300) and
        # bound entries inside a long column without materializing the matrix.
        step = chunk_rows if storage == "csr_matrix" else 1
        for first in range(0, major, step):
            last = min(major, first + step)
            lo, hi = int(pointers[first]), int(pointers[last])
            previous_index = None
            previous_major = None
            for start in range(lo, hi, chunk_rows * g):
                end = min(hi, start + chunk_rows * g)
                ix = indices[start:end]
                require(np.all(ix < minor) and np.all(ix >= 0), "Sparse index out of range")
                majors = np.searchsorted(pointers, np.arange(start, end), side="right") - 1
                require(not len(ix) or previous_major != int(majors[0])
                        or previous_index < int(ix[0]), "Sparse indices not strictly increasing")
                require(np.all((majors[1:] != majors[:-1]) | (ix[1:] > ix[:-1])),
                        "Sparse duplicate or unsorted indices")
                if len(ix):
                    previous_index, previous_major = int(ix[-1]), int(majors[-1])
                rows = majors if storage == "csr_matrix" else ix
                consume(data[start:end], rows)
        dtype = str(data.dtype)
    bad["unsafe_total"] |= (~np.isfinite(totals)) | (totals > 2**53)
    return totals, bad, {"storage": storage, "dtype": dtype,
                         "shape": list(shape), "invalid_value_counts": invalid_values,
                         "sum_dtype": "uint64", "quantile_dtype": "float64", "maximum_exact_total": 2**53}


def load_registry(path=REGISTRY):
    registry = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = registry["sections"]
    require(len(rows) == 19 and registry["expected_genes"] == 300, "Expected frozen 19-section/300-gene registry")
    require(len({r["section"] for r in rows}) == 19, "Duplicate section IDs in registry")
    require(len({(r["sample"], r["gen_fine"]) for r in rows}) == 19, "Overlapping registry selectors")
    return registry


def historical_counts(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    require(len(rows) == 19 and len({r["section"] for r in rows}) == 19,
            "Historical ledger must contain 19 unique sections")
    return {r["section"]: {"all_cells": int(r["all_cell_count"]),
                           "glial_cells": int(r["glial_count"])} for r in rows}


def audit_h5ad(path, *, historical_ledger=None, chunk_rows=4096):
    """Return aggregate audit and local exclusions; never modify the H5AD.

    The canonical registry is bundled and cannot be overridden by a CLI flag.
    Structural/identity errors raise ContractError. Invalid individual cells are
    excluded explicitly and flagged for review; historical discrepancies never
    change eligibility or force agreement. The historical ledger is an optional
    comparison only; the frozen registry and raw input define the audit.
    """
    require(chunk_rows > 0, "chunk_rows must be positive")
    path = Path(path).resolve()
    before = path.stat()
    source_hash = sha256_file(path)
    registry = load_registry()
    history = historical_counts(historical_ledger) if historical_ledger is not None else None
    if history is not None:
        require(set(history) == {r["section"] for r in registry["sections"]}, "Historical section IDs differ from registry")
    findings = []
    with h5py.File(path, "r") as f:
        required = ("layers/RNA", "obs", "var", "obs/sample", "obs/gen_fine",
                    "obs/cluster_coarse", "obsm/spatial")
        require(all(p in f for p in required), "Missing required H5AD structure: " +
                ", ".join(p for p in required if p not in f))
        cells, cell_key = axis_ids(f["obs"])
        genes, gene_key = axis_ids(f["var"])
        n, g = len(cells), len(genes)
        require(g == registry["expected_genes"], "Measured panel must contain exactly 300 unique genes")
        columns = {k: strings(f[f"obs/{k}"]) for k in ("sample", "gen_fine", "cluster_coarse")}
        require(all(len(v) == n for v in columns.values()), "Metadata length does not match cell axis")
        spatial = f["obsm/spatial"]
        require(isinstance(spatial, h5py.Dataset) and spatial.shape == (n, 2), "Expected spatial shape (n_cells, 2)")
        numeric_dtype(spatial.dtype, spatial.name)
        totals, reasons, counts = count_totals(f["layers/RNA"], (n, g), chunk_rows)
        reasons["invalid_spatial"] = np.zeros(n, dtype=bool)
        for start in range(0, n, chunk_rows):
            reasons["invalid_spatial"][start:start + chunk_rows] = ~np.isfinite(spatial[start:start + chunk_rows]).all(axis=1)
        reasons["missing_cell_type"] = np.array([not x.strip() for x in columns["cluster_coarse"]])
        reasons["missing_section_metadata"] = np.array([
            not a.strip() or not b.strip() for a, b in zip(columns["sample"], columns["gen_fine"])])
        section_index = np.full(n, -1, dtype=np.int16)
        for i, row in enumerate(registry["sections"]):
            mask = (columns["sample"] == row["sample"]) & (columns["gen_fine"] == row["gen_fine"])
            require(not np.any(section_index[mask] >= 0), "Overlapping section selections")
            section_index[mask] = i
        reasons["unregistered_section"] = (section_index < 0) & ~reasons["missing_section_metadata"]
        valid_counts = ~np.logical_or.reduce([reasons[k] for k in REASONS[:4]])
        reasons["zero_total"] = valid_counts & (totals == 0)
        eligible = ~np.logical_or.reduce(list(reasons.values()))
        structural = np.logical_or.reduce([reasons[k] for k in REASONS if k != "zero_total"])
        if np.any(structural):
            findings.append("Structurally invalid cells excluded; review reason counts and local exclusion rows.")
        sections = []
        for i, row in enumerate(registry["sections"]):
            selected = section_index == i
            kept = selected & eligible
            values = totals[kept]
            stats = dict(zip(QUANTILES, map(float, np.quantile(values, list(QUANTILES.values()), method="linear")))) if len(values) else dict.fromkeys(QUANTILES)
            result = {"section": row["section"], "all_cells": int(selected.sum()),
                      "eligible_cells": int(kept.sum()), "zero_total_cells": int((selected & reasons["zero_total"]).sum()),
                      "structurally_invalid_cells": int((selected & structural).sum()),
                      "excluded_cells": int((selected & ~eligible).sum()),
                      "selected_cell_order_sha256": ordered_hash(cells[selected]),
                      "eligible_cell_order_sha256": ordered_hash(cells[kept])}
            for prefix, population in (("all", selected), ("eligible", kept)):
                for label, raw in TYPE_LABELS.items():
                    result[f"{prefix}_{label}"] = int((population & (columns["cluster_coarse"] == raw)).sum())
                result[f"{prefix}_glial_cells"] = sum(result[f"{prefix}_{t}"] for t in TYPE_LABELS)
                result[f"{prefix}_other_cells"] = int(population.sum()) - result[f"{prefix}_glial_cells"]
            result.update({f"total_{k}": v for k, v in stats.items()})
            result.update(dict.fromkeys(("historical_all_cells", "historical_glial_cells",
                                         "historical_all_delta", "historical_glial_delta",
                                         "historical_counts_match")))
            if history is not None:
                expected = history[row["section"]]
                result.update({f"historical_{k}": v for k, v in expected.items()})
                result["historical_all_delta"] = result["all_cells"] - expected["all_cells"]
                result["historical_glial_delta"] = result["all_glial_cells"] - expected["glial_cells"]
                result["historical_counts_match"] = not (result["historical_all_delta"] or result["historical_glial_delta"])
                if not result["historical_counts_match"]:
                    findings.append(f"{row['section']}: aggregate counts differ from B6 ledger.")
            if not len(values):
                findings.append(f"{row['section']}: no eligible cells; common depth unavailable.")
            sections.append(result)
        medians = [r["total_median"] for r in sections]
        depth = min(medians) if all(m is not None for m in medians) else None
        # Unknown nonmissing section labels violate the fixed coverage contract.
        if np.any(reasons["unregistered_section"]):
            depth = None
            findings.append("Unregistered section metadata; common depth withheld.")
        excluded = [{"source_row": int(i), "section": registry["sections"][section_index[i]]["section"] if section_index[i] >= 0 else "",
                     "reasons": ";".join(k for k in REASONS if reasons[k][i])}
                    for i in np.flatnonzero(~eligible)]
        audit = {
            "schema": SCHEMA, "status": "fail" if depth is None else ("review_required" if findings else "pass"),
            "source": {"path": str(path), "bytes": before.st_size, "sha256": source_hash,
                       "identity_limit": "Content fingerprint and contract checks; no independent authoritative raw-file checksum supplied."},
            "implementation": {"module_sha256": sha256_file(__file__), "registry_sha256": sha256_file(REGISTRY)},
            "runtime": {"interpreter": str(Path(sys.executable).resolve()), "python": platform.python_version(),
                        "numpy": np.__version__, "h5py": h5py.__version__, "hdf5": h5py.version.hdf5_version},
            "schema_checks": {"required_paths": list(required), "cell_index": cell_key, "gene_index": gene_key,
                              "cell_ids_unique": True, "gene_ids_unique": True, "orientation": "cells_by_genes",
                              "gene_order_sha256": ordered_hash(genes), "cell_order_sha256": ordered_hash(cells),
                              "ordered_hash_encoding": "uint64-LE UTF-8 byte length followed by UTF-8 bytes, per identifier",
                              "spatial_shape": list(spatial.shape), "type_mapping": TYPE_LABELS},
            "counts": counts, "registry": registry,
            "policy": {"chunk_rows": chunk_rows, "quantile_method": "linear (median averages middle pair)",
                       "depth_population": "all eligible nonzero cells of each section; all 300 measured genes",
                       "exclusion_reasons": list(REASONS), "additional_expression_QC": False,
                       "comparison_population": "all selected cells before exclusions, matching B6 ledger semantics" if history is not None else None},
            "aggregate": {"all_cells": n, "genes": g, "registered_cells": int((section_index >= 0).sum()),
                          "eligible_cells": int(eligible.sum()), "excluded_cells": len(excluded),
                          "reason_counts": {k: int(v.sum()) for k, v in reasons.items()},
                          "all_glial_cells": sum(r["all_glial_cells"] for r in sections),
                          "eligible_glial_cells": sum(r["eligible_glial_cells"] for r in sections)},
            "historical_ledger": {"path": str(Path(historical_ledger).resolve()), "sha256": sha256_file(historical_ledger)} if history is not None else None,
            "sections": sections, "proposed_common_depth": depth,
            "minimizing_sections": [r["section"] for r in sections if depth is not None and r["total_median"] == depth],
            "findings": findings,
            "limits": ["No SCTransform executed; no generated response certified.",
                       "No external reference gene list or raw-file checksum authenticated independently.",
                       "The fixed 91-gene modeling panel and R environment are separate later checks.",
                       "Full-data depth only; not approved for training-only holdout preprocessing."]}
    after = path.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Input changed during audit")
    return audit, excluded


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_reports(audit, excluded, output_dir):
    """Create a fresh artifact directory. Never overwrite prior evidence."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / "audit.json", audit)
    write_csv(output / "sections.csv", audit["sections"], list(audit["sections"][0]))
    write_csv(output / "exclusions.csv", excluded, ["source_row", "section", "reasons"])
    lines = ["# SCTransform raw-input preflight", "", f"Status: **{audit['status']}**.",
             f"Source SHA-256: `{audit['source']['sha256']}`.",
             f"Size: {audit['source']['bytes']} bytes.",
             f"Cells: {audit['aggregate']['all_cells']}; eligible: {audit['aggregate']['eligible_cells']}; genes: {audit['aggregate']['genes']}.",
             f"Proposed common depth: **{audit['proposed_common_depth']}**.",
             "", "| Section | All | Eligible | MIC | AST | OGC | Other | Zero | Median | B6 match |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
    for r in audit["sections"]:
        lines.append("| " + " | ".join(str(r[k]) if r[k] is not None else "not compared" for k in ("section", "all_cells", "eligible_cells", "eligible_MIC", "eligible_AST", "eligible_OGC", "eligible_other_cells", "zero_total_cells", "total_median", "historical_counts_match")) + " |")
    success = "No contract or historical-count discrepancies found." if audit["historical_ledger"] is not None else "No contract discrepancies found; historical comparison not requested."
    lines += ["", "MIC/AST/OGC/Other counts above are eligible cells. Quantiles and pre-exclusion counts are in sections.csv.",
              "", "Findings:", ""] + [f"- {s}" for s in (audit["findings"] or [success])]
    lines += ["", "Limits:", ""] + [f"- {s}" for s in audit["limits"]]
    lines += ["", "Execution provenance:", "", "```json",
              json.dumps({"runtime": audit["runtime"], "implementation": audit["implementation"],
                          "invocation": audit.get("invocation")}, indent=2, sort_keys=True), "```"]
    (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    manifest = {"schema": SCHEMA + ".manifest", "source": audit["source"],
                "implementation": audit["implementation"], "runtime": audit["runtime"],
                "invocation": audit.get("invocation"), "historical_ledger": audit["historical_ledger"],
                "findings": audit["findings"], "limits": audit["limits"],
                "schema_checks": audit["schema_checks"], "aggregate": audit["aggregate"],
                "status": audit["status"], "proposed_common_depth": audit["proposed_common_depth"],
                "minimizing_sections": audit["minimizing_sections"],
                "artifacts": {p.name: {"bytes": p.stat().st_size, "sha256": sha256_file(p)} for p in sorted(output.iterdir())}}
    write_json(output / "manifest.json", manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("h5ad", type=Path)
    parser.add_argument("--historical-ledger", type=Path, help="Optional B6 section recipe CSV cross-check")
    parser.add_argument("--output-dir", type=Path, required=True, help="Fresh Git-ignored or external artifact directory")
    parser.add_argument("--chunk-rows", type=int, default=4096)
    args = parser.parse_args(argv)
    try:
        require(not args.output_dir.exists(), "Output directory already exists; use a fresh path")
        audit, excluded = audit_h5ad(args.h5ad, historical_ledger=args.historical_ledger, chunk_rows=args.chunk_rows)
        audit["invocation"] = {"working_directory": str(Path.cwd()),
                               "argv": [str(Path(sys.executable).resolve()), "-m", "bsfm.preprocessing.raw_preflight",
                                        *(sys.argv[1:] if argv is None else list(argv))]}
        write_reports(audit, excluded, args.output_dir)
    except (ContractError, OSError, KeyError, ValueError) as error:
        print(f"Preflight failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"status": audit["status"], "proposed_common_depth": audit["proposed_common_depth"], "output_dir": str(args.output_dir)}, sort_keys=True))
    return {"pass": 0, "review_required": 1, "fail": 2}[audit["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
