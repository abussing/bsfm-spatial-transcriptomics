"""Independent closed-file validator; never imports the bundle writer or fits SCT."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np

from .raw_preflight import require, sha256_file
from .execution_evidence import authenticate_process, scan_log
from .response_contract import (CONFIG, META, AXES, contract, load_json, save_json,
    file_record, validate_json, identities, code_identity, raw_section, readback, inventory)


def equal(actual, expected, message):
    require(np.array_equal(actual, expected), message)


def check_response(path, raw, panel, spec, cfg, reconstructed):
    """Reopen HDF5 and derive expectations from source metadata, not writer helpers."""
    with h5py.File(path, "r") as f:
        found = []
        f.visititems(lambda name, item: found.append('/'+name) if isinstance(item, h5py.Dataset) else None)
        require(set(found) == set(spec["datasets"]), "Unexpected or missing HDF5 datasets")
        require(json.loads(f.attrs["coordinates_contract"]) == spec["coordinates"], "Coordinate contract changed")
        require(f.attrs["schema"] == spec["bundle_schema"], "HDF5 schema changed")
        codes = raw["metadata"]["cluster_coarse"]
        selected = np.concatenate([np.flatnonzero(codes == x) for x in ("Mic", "AST", "OGC")])
        groups = np.array([np.count_nonzero(codes == x) for x in ("Mic", "AST", "OGC")], dtype=np.int64)
        require(np.all(groups > 0), "Missing modeled cell type")
        types = np.repeat(np.arange(3), groups)
        genes = np.array(panel["raw_300_positions_zero_based"])
        lengths = {"N": len(raw["cells"]), "M": len(selected)}
        values = {}
        physical = {}
        for name, rule in spec["datasets"].items():
            d = f[name]
            require(d.shape == tuple(lengths.get(n, n) for n in rule["shape"]), f"Shape mismatch: {name}")
            require(d.compression == cfg["storage"]["compression"] and d.compression_opts == cfg["storage"]["compression_opts"], "Unrecorded storage compression")
            if rule["dtype"] == "utf8":
                info = h5py.check_string_dtype(d.dtype)
                require(info is not None and info.encoding == "utf-8", "Wrong string encoding")
                values[name] = d.asstr()[:]
                require(not d.shuffle, "Unexpected string shuffle")
            else:
                require(d.dtype.str == {"float64": "<f8", "int64": "<i8"}[rule["dtype"]], "Wrong numeric dtype/endian")
                values[name] = d[:]
                require(np.isfinite(values[name]).all(), f"Nonfinite values: {name}")
                require(d.shuffle == cfg["storage"]["shuffle"], "Unexpected numeric shuffle")
            require(json.loads(d.attrs["axis_refs"]) == [AXES[a] for a in rule["axes"]], "Dataset axis references changed")
            physical[name] = {"chunks": list(d.chunks), "compression": d.compression,
                              "compression_opts": d.compression_opts, "shuffle": bool(d.shuffle)}
        expected = {
            "/axes/genes300/ids": raw["genes"], "/axes/genes300/raw_gene_index": np.arange(300),
            "/axes/genes91/ids": panel["genes"], "/axes/genes91/raw_gene_index": genes,
            "/axes/genes91/all_gene_index": genes,
            "/axes/cells_all/ids": raw["cells"], "/axes/cells_all/source_row": raw["rows"],
            "/axes/cells_model/ids": raw["cells"][selected], "/axes/cells_model/source_row": raw["rows"][selected],
            "/axes/cells_model/all_cell_index": selected,
            "/axes/types/labels": ["MIC", "AST", "OGC"], "/axes/types/codes": [0, 1, 2],
            "/axes/coordinates/labels": ["center_y", "center_x"],
            "/centering/group_sizes": groups, "/metadata/model_type_code": types,
            "/coordinates/all_source": raw["coordinates"], "/coordinates/model_source": raw["coordinates"][selected]}
        expected.update({"/metadata/all/"+k: raw["metadata"][k] for k in META})
        for name, x in expected.items():
            equal(values[name], x, f"Identity/order/membership mismatch: {name}")
        for name in AXES.values():
            require(len(set(values[name])) == len(values[name]), "Duplicate axis identities")
        c = values["/all/corrected_counts"]
        l = values["/all/log1p_response"]
        require(np.all(c >= 0) and np.all(c == np.floor(c)), "Invalid corrected counts")
        # R readback uses the same pinned math implementation for exact log1p.
        # NumPy's log1p is not assumed bitwise equal to R's libm operation.
        equal(c, reconstructed["corrected"], "Saved-model corrected counts differ")
        equal(l, reconstructed["response"], "Exact saved-model log1p equality failed")
        chosen = l[np.ix_(genes, selected)]
        equal(values["/model/uncentered_response"], chosen, "Selected response differs")
        mu = values["/centering/means"]
        y = values["/model/centered_response"]
        tol = cfg["tolerances"]
        # Independent reduction: separate per-gene sums over each actual group.
        measured = np.array([[np.sum(chosen[g, types == t], dtype=np.float64) / groups[t]
                              for t in range(3)] for g in range(91)])
        require(np.allclose(mu, measured, atol=tol["means_atol"], rtol=tol["means_rtol"]), "Centering means differ")
        equal(y, chosen - mu[:, types], "Centered response is not exactly L minus recorded means")
        error = float(np.max(np.abs(y + mu[:, types] - chosen)))
        residual = float(max(np.max(np.abs(y[:, types == t].mean(axis=1))) for t in range(3)))
        require(np.allclose(y + mu[:, types], chosen, atol=tol["reconstruction_atol"], rtol=tol["reconstruction_rtol"]), "Reconstruction tolerance exceeded")
        require(residual <= tol["centering_atol"], "Centering residual exceeded")
        datasets, axes = inventory(f, spec)
        for name, rule in spec["datasets"].items():
            require(json.loads(f[name].attrs["axis_hashes"]) == [axes[a]["ordered_sha256"] for a in rule["axes"]], "Dataset axis hashes changed")
    metrics = {"all_invariants_passed": True, "readback_passed": True,
               "max_abs_centering_mean": residual, "max_abs_reconstruction_error": error,
               **{k: tol[k] for k in ("centering_atol", "reconstruction_atol", "reconstruction_rtol")}}
    return {"metrics": metrics, "datasets": datasets, "axes": axes, "physical_storage": physical,
            "group_sizes": groups.tolist(), "max_abs_mean_recalculation_difference": float(np.max(np.abs(mu-measured))),
            "dimensions": {"all_cells": lengths["N"], "model_cells": lengths["M"], "all_genes": 300, "model_genes": 91, "types": 3}}


def check_execution(execution, raw, config, envroot):
    cfg, _, _, _ = contract(config)
    require(execution["schema"] == "bsfm.single-section-execution.v1", "Execution schema mismatch")
    require(execution["identities"] == identities(config, envroot), "Configuration/environment identity mismatch")
    require(execution["code"] == code_identity(), "Executed code identity differs from this validator checkout")
    require(execution["source"] == raw["source"], "Executed source identity mismatch")
    require(execution["run_configuration"] == cfg, "Execution settings differ")
    require(execution["environment_root"] == str(envroot.resolve()), "Environment root differs")
    fit = execution["normalization"]["report"]
    require(fit["status"] == "pass" and fit["effective_method"] == "glmGamPoi_offset", "Fit failed or fell back")
    require(fit["depth"] == 124 and fit["seed"] == 1448145 and fit["RNG"] == ["Mersenne-Twister", "Inversion", "Rejection"], "Depth/RNG changed")
    require(fit["input_cells"] == fit["fitting_cells"] == len(raw["cells"]) and fit["input_genes"] == 300, "Fit population changed")
    require(fit["gene_availability"] == {"modeled_by_SCT": 300, "unavailable": []}, "Required gene model unavailable")
    require(fit["versions"] == {"Seurat":"5.4.0", "SeuratObject":"5.4.0", "sctransform":"0.4.3", "Matrix":"1.7-4", "glmGamPoi":"1.22.0"}, "Package versions changed")
    require(fit["R"] == "4.5.3" and fit["Bioconductor"] == "3.22", "R/Bioconductor changed")
    require(set(fit["threads"].values()) == {"1"}, "Thread settings changed")
    for process in [execution["normalization"]["process"], execution["transport_readback"]["process"]]:
        authenticate_process(process)
    for phase in ("normalization", "transport_readback"):
        warnings = execution[phase]["report"].get("warnings", [])
        require(not scan_log(json.dumps(warnings).encode("utf-8"))["stack_imbalance_detected"],
                "Recorded stack imbalance warning")


def validate_payload(bundle, source, envroot, config, work):
    """Pre-manifest validation of closed payloads; cannot declare a final bundle."""
    cfg, panel, spec, _ = contract(config)
    execution = load_json(bundle / "execution.json")
    raw = raw_section(source, execution["section"], config)
    check_execution(execution, raw, config, envroot)
    expected_fit = next(a for a in execution["normalization"]["report"]["artifacts"] if a["name"] == "fit.rds")
    require(file_record(bundle / "fit.rds") == {"path":"fit.rds", "bytes":expected_fit["bytes"], "sha256":expected_fit["sha256"]}, "Fitted object identity mismatch")
    session = next(a for a in execution["normalization"]["report"]["artifacts"] if a["name"] == "session.txt")
    require(sha256_file(bundle / "session.txt") == session["sha256"], "Session record changed")
    reconstructed, rr = readback(envroot, raw, bundle / "fit.rds", work, 124)
    require(rr["report"]["semantic_sha256"] == execution["normalization"]["report"]["semantic_sha256"], "Readback semantic hashes differ")
    require(rr["report"]["effective_arguments"] == execution["transport_readback"]["report"]["effective_arguments"], "Effective fit arguments changed")
    result = check_response(bundle / "response.h5", raw, panel, spec, cfg, reconstructed)
    require(result["physical_storage"] == execution["physical_storage"], "HDF5 storage record differs")
    return {"schema": "bsfm.response-validation.v1", "status": "pass", "section": execution["section"],
            "source": raw["source"], "animal_label": str(raw["metadata"]["gen"][0]),
            "genotype": str(raw["metadata"]["gen_coarse"][0]), "identities": identities(config, envroot),
            "code_commit": execution["code"]["commit"], "tolerances": cfg["tolerances"],
            "exact_log1p_check": "Pinned R log1p after independent saved-model recorrection; exact binary payload equality",
            "independent_readback": rr, **result}


def check_final_metadata(bundle, manifest, report, spec):
    validate_json(manifest, "response-manifest.schema.json")
    authenticate_process(report["independent_readback"]["process"])
    for key in ("section", "source", "animal_label", "genotype", "identities", "code_commit", "datasets", "axes", "dimensions"):
        require(manifest[key] == report[key], f"Manifest disagreement: {key}")
    require(manifest["validation"] == report["metrics"], "Manifest metrics disagree")
    require(manifest["regime"] == spec["regime"] and manifest["coordinates"] == spec["coordinates"], "Regime or coordinates changed")
    require(set(p.name for p in bundle.iterdir()) == set(spec["required_files"]) | {"manifest.json"}, "Unexpected or incomplete bundle contents")
    for name in spec["required_files"]:
        require((bundle / name).is_file() and not (bundle / name).is_symlink(), "Artifact is not a regular file")
        require(manifest["artifacts"][name] == file_record(bundle / name), f"Artifact hash/size mismatch: {name}")


def validate_bundle(bundle, source, envroot, config, work):
    require(not any(p.startswith('.attempt-') for p in bundle.parts), "Temporary attempt cannot be consumed")
    manifest = load_json(bundle / "manifest.json")
    require(bundle.name == manifest["section"], "Final directory must identify section")
    _, _, spec, _ = contract(config)
    recorded = load_json(bundle / "validation.json")
    # Check hashes/schema before expensive recorrection; then independently repeat all checks.
    check_final_metadata(bundle, manifest, recorded, spec)
    fresh = validate_payload(bundle, source, envroot, config, work)
    for key in ("metrics", "datasets", "axes", "dimensions", "group_sizes", "tolerances", "physical_storage"):
        require(recorded[key] == fresh[key], f"Saved validation differs from fresh readback: {key}")
    check_final_metadata(bundle, manifest, fresh, spec)
    return fresh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, required=True)
    p.add_argument("--raw-source", type=Path, required=True)
    p.add_argument("--environment", type=Path, required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--work-dir", type=Path, required=True)
    args = p.parse_args()
    from .response_contract import REPO
    require(not args.work_dir.resolve().is_relative_to(REPO), "Readback artifacts must stay outside Git")
    result = validate_bundle(args.bundle.resolve(), args.raw_source.resolve(), args.environment.resolve(), args.config, args.work_dir.resolve())
    save_json(args.work_dir / "validation-result.json", result)
    print(json.dumps({"status": result["status"], "section": result["section"], **result["metrics"]}))


if __name__ == "__main__":
    main()
