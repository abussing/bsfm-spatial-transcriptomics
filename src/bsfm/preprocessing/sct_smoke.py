"""Bounded SCT validation orchestrator: synthetic gate, then optionally S00 only.

No package installation, gene-panel selection, centering, or model initialization.
Expression/identifiers and R outputs stay in a fresh external artifact directory.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import h5py
import numpy as np
import psutil

from .raw_preflight import (REGISTRY, axis_ids, load_registry, ordered_hash,
                            require, sha256_file, strings, text)
from .execution_evidence import embed_log, authenticate_log

SOURCE_SHA256 = "d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38"
SECTION = "S00__Trem2_5xFAD4"
SEED = 1448145
RUNNER = Path(__file__).with_name("sct_validation.R")


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def artifact(path):
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def write_input(directory, counts, genes, cells, provenance):
    """counts is cells x genes; R reads its little-endian C-order bytes as G x N."""
    counts = np.asarray(counts)
    require(counts.shape == (len(cells), len(genes)), "Input shape mismatch")
    require(len(set(genes)) == len(genes) and len(set(cells)) == len(cells), "Duplicate IDs")
    require(all(str(x).strip() for x in list(genes) + list(cells)), "Empty IDs")
    require(np.all(np.isfinite(counts) & (counts >= 0) & (counts == np.floor(counts))), "Invalid counts")
    require(np.all(counts.sum(axis=1) > 0), "Zero-total cell")
    directory.mkdir(parents=True, exist_ok=False)
    counts.astype("<f8").tofile(directory / "counts.f64")
    write_json(directory / "genes.json", list(genes))
    write_json(directory / "cells.json", list(cells))
    meta = {"schema": "bsfm.sct-validation-input.v1", "shape": [len(genes), len(cells)],
            "storage": "little-endian float64; genes vary fastest; genes x cells in R",
            "gene_order_sha256": ordered_hash(genes), "cell_order_sha256": ordered_hash(cells),
            "source": provenance,
            "files": [artifact(directory / n) for n in ("counts.f64", "genes.json", "cells.json")]}
    write_json(directory / "input.json", meta)
    return meta


def synthetic_inputs(root):
    rng = np.random.default_rng(SEED)
    genes = [f"G{i:03d}" for i in range(300)]
    matrices = []
    for name, n, multiplier in [("synthetic-A", 240, 1.), ("synthetic-B", 320, 2.5)]:
        gene_mean = np.geomspace(.3, 8, 300)
        cell_depth = rng.lognormal(0, .45, n) * multiplier
        mean = cell_depth[:, None] * gene_mean[None, :]
        counts = rng.negative_binomial(3., 3. / (3. + mean))
        write_input(root / name, counts, genes, [f"{name}-{i:04d}" for i in range(n)],
                    {"kind": "synthetic", "generator": "NumPy PCG64 negative_binomial", "seed": SEED})
        matrices.append(counts)
    medians = [float(np.median(x.sum(axis=1))) for x in matrices]
    require(medians[0] != medians[1], "Fixture must exercise unequal correction depths")
    return {"medians": medians, "common_depth": min(medians)}


def selected_counts(node, rows, n_genes):
    """Read only the selected raw rows, bounded by 1024 cells (dense/CSR/CSC)."""
    result = np.zeros((len(rows), n_genes), dtype=np.float64)
    if isinstance(node, h5py.Dataset):
        for first in range(0, len(rows), 1024):
            result[first:first+1024] = node[rows[first:first+1024], :]
    elif text(node.attrs.get("encoding-type", "")) == "csr_matrix":
        for target, row in enumerate(rows):
            lo, hi = map(int, node["indptr"][row:row+2])
            result[target, node["indices"][lo:hi]] = node["data"][lo:hi]
    elif text(node.attrs.get("encoding-type", "")) == "csc_matrix":
        for gene in range(n_genes):
            lo, hi = map(int, node["indptr"][gene:gene+2])
            # Bound each scan, including columns with many nonzeros.
            for start in range(lo, hi, 1024*n_genes):
                stop = min(hi, start + 1024*n_genes)
                ix = node["indices"][start:stop]
                positions = np.searchsorted(rows, ix)
                valid = positions < len(rows)
                valid[valid] &= rows[positions[valid]] == ix[valid]
                result[positions[valid], gene] = node["data"][start:stop][valid]
    else:
        raise ValueError("Unsupported raw count encoding")
    return result


def s00_input(source, root, repository):
    before = source.stat()
    require(before.st_size == 5483600151, "Raw source size changed")
    require(sha256_file(source) == SOURCE_SHA256, "Raw source fingerprint mismatch")
    registry = load_registry()
    section = next(x for x in registry["sections"] if x["section"] == SECTION)
    with h5py.File(source, "r") as handle:
        genes, _ = axis_ids(handle["var"])
        cells, _ = axis_ids(handle["obs"])
        samples = strings(handle["obs/sample"])
        fine = strings(handle["obs/gen_fine"])
        rows = np.flatnonzero((samples == section["sample"]) & (fine == section["gen_fine"]))
        require(len(genes) == 300 and len(rows) == 20719, "Frozen S00 population mismatch")
        counts = selected_counts(handle["layers/RNA"], rows, len(genes))
        cell_ids = cells[rows]
    table = repository / "docs/preprocessing/audits/20261030_raw/sections.csv"
    with table.open(newline="") as stream:
        accepted = next(r for r in csv.DictReader(stream) if r["section"] == SECTION)
    require(ordered_hash(cell_ids) == accepted["eligible_cell_order_sha256"], "S00 cell identity/order mismatch")
    require(float(np.median(counts.sum(axis=1))) == 124, "S00 median depth changed")
    after = source.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Source changed during extraction")
    provenance = {"kind": "accepted_raw_S00", "path": str(source.resolve()),
                  "sha256": SOURCE_SHA256, "layer": "layers/RNA", "section": SECTION,
                  "registry_sha256": sha256_file(REGISTRY), "no_exclusions": True}
    meta = write_input(root / "S00-input", counts, genes, cell_ids, provenance)
    subset = np.linspace(0, len(rows)-1, 1024, dtype=int)
    write_input(root / "S00-repeat-subset", counts[subset], genes, cell_ids[subset],
                {**provenance, "scope": "determinism check only; 1024 evenly spaced source-ordered S00 cells",
                 "subset_rule": "numpy.linspace(0, 20718, 1024, dtype=int)", "common_depth": 124})
    return meta


def run_r(envroot, input_dir, output, depth, timeout=900, memory_limit=8*1024**3,
          runner=None, extra_args=None):
    # Launch the actual interpreter, not bin/Rscript.exe's short-lived wrapper,
    # so the memory monitor measures the R process that performs the fit.
    command = [str(envroot / "R-4.5.3/bin/x64/Rscript.exe"), "--vanilla", str((runner or RUNNER).resolve()),
               str(envroot), str(input_dir), str(output), str(depth), str(SEED)]
    if extra_args is not None:
        command = command[:3] + [str(x) for x in extra_args]
    env = os.environ.copy()
    env.update({"R_LIBS_USER": str(envroot / "library"), "R_LIBS_SITE": "",
                "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
                "VECLIB_MAXIMUM_THREADS": "1", "LANG": "C", "LC_ALL": "C",
                "R_ENVIRON_USER": "", "R_PROFILE_USER": ""})
    log = output.with_suffix(".log")
    start = time.monotonic()
    peak = 0
    failure = None
    with log.open("wb") as stream:
        process = subprocess.Popen(command, env=env, stdout=stream, stderr=subprocess.STDOUT)
        monitor = psutil.Process(process.pid)
        while process.poll() is None:
            try:
                info = monitor.memory_info()
                peak = max(peak, info.rss, getattr(info, "peak_wset", 0))
            except psutil.NoSuchProcess:
                pass
            if time.monotonic()-start > timeout or peak > memory_limit:
                failure = "runtime_or_memory_limit_exceeded"
                process.kill()
                break
            time.sleep(.2)
        code = process.wait()
    record = {"command": command, "exit_code": code, "elapsed_seconds": time.monotonic()-start,
              "peak_working_set_bytes": peak, "memory_observation": "Windows peak_wset sampled every 0.2 s; main R process",
              "limits": {"seconds": timeout, "working_set_bytes": memory_limit},
              "log": {"path": str(log), "name": log.name, **embed_log(log.read_bytes())},
              "failure": failure}
    write_json(output.with_suffix(".process.json"), record)
    require(code == 0 and failure is None, f"R validation failed; inspect {log}")
    authenticate_log(record["log"])
    report = json.loads((output / "report.json").read_text())
    require(report["status"] == "pass", "R report failed")
    return {"process": record, "report": report, "output": str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-source", type=Path, help="Enables only S00, after synthetic checks")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[3]
    root = args.output_dir.resolve()
    require(not root.exists(), "Use a fresh output directory")
    require(not root.is_relative_to(repository), "Validation artifacts must be outside Git repository")
    envroot = args.environment.resolve()
    root.mkdir(parents=True)
    report = {"schema": "bsfm.sct-smoke.v1", "status": "running",
              "source_files": {str(p.relative_to(repository)): sha256_file(p)
                               for p in [Path(__file__).resolve(), RUNNER, RUNNER.with_name("sct_core.R"),
                                         Path(__file__).with_name("execution_evidence.py"), REGISTRY,
                                         Path(__file__).with_name("raw_preflight.py"),
                                         repository / "environment/sctransform/validation-spec.json"]},
              "invocation": [sys.executable, *sys.argv],
              "environment_source_lock_sha256": sha256_file(envroot / "source-lock.json"),
              "runs": {}}
    try:
        fixture = synthetic_inputs(root)
        report["synthetic_fixture"] = fixture
        for name in ("synthetic-A", "synthetic-B"):
            for repeat in (1, 2):
                key = f"{name}-run{repeat}"
                report["runs"][key] = run_r(envroot, root / name, root / key, fixture["common_depth"])
            first = report["runs"][f"{name}-run1"]["report"]["semantic_sha256"]
            second = report["runs"][f"{name}-run2"]["report"]["semantic_sha256"]
            require(first == second, f"Fresh-session repeat differs: {name}")
        report["synthetic_gate"] = "pass"
        write_json(root / "run-manifest.json", report)
        if args.raw_source:
            report["S00_input"] = s00_input(args.raw_source, root, repository)
            report["runs"]["S00-full"] = run_r(envroot, root / "S00-input", root / "S00-full", 124)
            for repeat in (1, 2):
                key = f"S00-subset-run{repeat}"
                report["runs"][key] = run_r(envroot, root / "S00-repeat-subset", root / key, 124)
            require(report["runs"]["S00-subset-run1"]["report"]["semantic_sha256"] ==
                    report["runs"]["S00-subset-run2"]["report"]["semantic_sha256"], "S00 subset repeat differs")
            report["S00_gate"] = "pass"
        report["status"] = "pass"
    except Exception as exc:
        report["status"] = "fail"
        report["error"] = str(exc)
        raise
    finally:
        write_json(root / "run-manifest.json", report)
    print(json.dumps({"status": report["status"], "output": str(root),
                      "synthetic": report.get("synthetic_gate"), "S00": report.get("S00_gate")}))


if __name__ == "__main__":
    main()
