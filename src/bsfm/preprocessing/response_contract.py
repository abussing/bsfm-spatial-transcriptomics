"""Shared identity/transport primitives, not response construction or validation."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

import h5py
import numpy as np
from jsonschema import Draft202012Validator

from .raw_preflight import axis_ids, ordered_hash, require, sha256_file, strings
from .sct_smoke import selected_counts, write_input, run_r

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO / "config/preprocessing/single-section-run.json"
READBACK = Path(__file__).with_name("sct_readback.R")
META = ("sample", "gen_fine", "gen", "gen_coarse", "cluster_coarse",
        "coarse_batch", "region_labels", "region_labels_coarse")
AXES = {"genes300": "/axes/genes300/ids", "genes91": "/axes/genes91/ids",
        "cells_all": "/axes/cells_all/ids", "cells_model": "/axes/cells_model/ids",
        "types": "/axes/types/labels", "coordinates": "/axes/coordinates/labels"}


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save_json(path, value):
    """Close and flush metadata before any completion/promotion decision."""
    with Path(path).open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())


def file_record(path):
    path = Path(path)
    return {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def validate_json(value, schema_name):
    Draft202012Validator(load_json(REPO / "schemas/preprocessing" / schema_name)).validate(value)


def contract(config=CONFIG):
    require(sha256_file(config) == sha256_file(CONFIG), "Unrecognized run configuration override")
    cfg = load_json(config)
    require(cfg["normalization"] == {"depth":124, "seed":1448145, "threads":1,
            "effective_method":"glmGamPoi_offset", "vst_flavor":"v2", "all_eligible_cells":True,
            "input_genes":300}, "Normalization configuration changed")
    require(cfg["tolerances"] == {"centering_atol":1e-12, "reconstruction_atol":1e-15,
            "reconstruction_rtol":1e-14, "means_atol":1e-14, "means_rtol":1e-14}, "Unreviewed numeric tolerances")
    for path, digest in cfg["frozen_files"].items():
        require(sha256_file(REPO / path) == digest, f"Frozen identity changed: {path}")
    panel = load_json(REPO / "config/preprocessing/modeling-panel.json")
    spec = load_json(REPO / "config/preprocessing/response-bundle.json")
    validate_json(panel, "modeling-panel.schema.json")
    validate_json(spec, "response-bundle.schema.json")
    require(ordered_hash(panel["genes"]) == panel["ordered_hash"]["value"], "Panel content/hash mismatch")
    registry = load_json(REPO / "src/bsfm/preprocessing/sections.json")
    return cfg, panel, spec, registry


def identities(config, envroot):
    cfg, panel, _, _ = contract(config)
    for name in ("source-lock.json", "renv.lock"):
        require(sha256_file(envroot / name) == cfg["environment_files"][name],
                f"Environment lock mismatch: {name}")
    return {"panel_registry_sha256": cfg["frozen_files"]["config/preprocessing/modeling-panel.json"],
            "panel_order_sha256": panel["ordered_hash"]["value"],
            "section_registry_sha256": cfg["frozen_files"]["src/bsfm/preprocessing/sections.json"],
            "bundle_spec_sha256": cfg["frozen_files"]["config/preprocessing/response-bundle.json"],
            "run_spec_sha256": sha256_file(config),
            "environment_source_lock_sha256": sha256_file(envroot / "source-lock.json"),
            "renv_lock_sha256": sha256_file(envroot / "renv.lock")}


def code_identity():
    sources = sorted(Path(__file__).parent.glob("*.py")) + sorted(Path(__file__).parent.glob("*.R"))
    return {"commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
            "source_files": {p.relative_to(REPO).as_posix(): sha256_file(p) for p in sources},
            "execution_authority": "User-authorized local review gate; source hashes identify uncommitted implementation"}


def raw_section(source, section, config=CONFIG):
    """Authenticate the entire source; read only selected expression rows."""
    _, panel, _, reg = contract(config)
    matches = [s for s in reg["sections"] if s["section"] == section]
    require(len(matches) == 1, "Unknown or ambiguous registered section")
    selector = matches[0]
    audit = load_json(REPO / "docs/preprocessing/audits/20261030_raw/manifest.json")
    before = source.stat()
    require(before.st_size == audit["source"]["bytes"], "Raw source size mismatch")
    require(sha256_file(source) == audit["source"]["sha256"], "Raw source fingerprint mismatch")
    with h5py.File(source, "r") as f:
        genes, _ = axis_ids(f["var"])
        cells, _ = axis_ids(f["obs"])
        require(ordered_hash(genes) == audit["schema_checks"]["gene_order_sha256"], "Raw gene axis mismatch")
        require(ordered_hash(cells) == audit["schema_checks"]["cell_order_sha256"], "Raw cell axis mismatch")
        metadata = {k: strings(f["obs/"+k]) for k in META}
        rows = np.flatnonzero((metadata["sample"] == selector["sample"]) &
                              (metadata["gen_fine"] == selector["gen_fine"]))
        metadata = {k: v[rows] for k, v in metadata.items()}
        xy = f["obsm/spatial"][rows]
        require(np.array_equal(xy, np.column_stack((f["obs/center_y"][rows], f["obs/center_x"][rows]))),
                "Coordinate source columns differ")
        counts = selected_counts(f["layers/RNA"], rows, len(genes))
        cells = cells[rows]
    # This v1 accepts only the audited immutable source, whose eligible set has no exclusions.
    require(np.isfinite(counts).all() and np.all(counts >= 0) and np.all(counts == np.floor(counts)), "Invalid counts")
    require(np.all(counts.sum(1) > 0) and np.isfinite(xy).all(), "Unexpected excluded cells")
    require(all(all(str(x).strip() for x in v) for v in metadata.values()), "Missing metadata")
    require(len(genes) == 300 and np.array_equal(genes[panel["raw_300_positions_zero_based"]], panel["genes"]), "Panel/raw mapping mismatch")
    with (REPO / "docs/preprocessing/audits/20261030_raw/sections.csv").open(newline="") as f:
        accepted = next(r for r in csv.DictReader(f) if r["section"] == section)
    require(len(rows) == int(accepted["eligible_cells"]) and
            ordered_hash(cells) == accepted["eligible_cell_order_sha256"], "Eligible population changed")
    for label, canonical in (("Mic", "MIC"), ("AST", "AST"), ("OGC", "OGC")):
        require(int(np.sum(metadata["cluster_coarse"] == label)) == int(accepted["eligible_"+canonical]), "Type counts changed")
    require(float(np.median(counts.sum(1))) == float(accepted["total_median"]), "Raw median changed")
    require(len(set(metadata["gen"])) == len(set(metadata["gen_coarse"])) == 1, "Ambiguous animal/genotype")
    after = source.stat()
    require((before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), "Source changed while reading")
    return {"genes": genes, "cells": cells, "rows": rows, "coordinates": xy,
            "metadata": metadata, "counts": counts,
            "source": {"path": str(source.resolve()), "bytes": before.st_size, "sha256": audit["source"]["sha256"]}}


def readback(envroot, source_data, fit, work, depth, accepted=None):
    """Fresh R process; saved-model correction only, never fitting."""
    work.mkdir(parents=True, exist_ok=False)
    write_input(work / "input", source_data["counts"], source_data["genes"], source_data["cells"], source_data["source"])
    args = [envroot, work / "input", fit, work / "output", depth]
    if accepted is not None:
        args.append(accepted)
    record = run_r(envroot, None, work / "output", depth, runner=READBACK, extra_args=args)
    shape = (len(source_data["genes"]), len(source_data["cells"]))
    arrays = {k: np.fromfile(work / "output" / (k+".f64"), dtype="<f8").reshape(shape)
              for k in ("corrected", "response")}
    require(load_json(work / "output/genes.json") == list(source_data["genes"]), "Readback gene order mismatch")
    require(load_json(work / "output/fitting-cells.json") == list(source_data["cells"]), "Readback fitting cells mismatch")
    return arrays, record


def payload_hash(values, dtype):
    if dtype == "utf8":
        return ordered_hash(np.asarray(values).reshape(-1))
    return hashlib.sha256(np.asarray(values, dtype={"float64": "<f8", "int64": "<i8"}[dtype]).tobytes(order="C")).hexdigest()


def inventory(h5, spec):
    datasets = {}
    for path, rule in spec["datasets"].items():
        d = h5[path]
        values = d.asstr()[:] if rule["dtype"] == "utf8" else d[:]
        datasets[path] = {"shape": list(d.shape), "dtype": rule["dtype"], "axes": rule["axes"],
                          "semantic_sha256": payload_hash(values, rule["dtype"])}
    axes = {name: {"ids_dataset": path, "length": len(h5[path]),
                   "ordered_sha256": ordered_hash(h5[path].asstr()[:])} for name, path in AXES.items()}
    return datasets, axes
