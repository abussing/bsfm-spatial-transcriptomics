"""Canonical single-section runner. No multi-section launcher or holdout mode."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

import h5py
import numpy as np

from .raw_preflight import require, ordered_hash
from .sct_smoke import write_input, run_r
from .response_contract import (REPO, CONFIG, META, AXES, contract, identities, code_identity,
    raw_section, readback, save_json, file_record, inventory)
from .response_validate import validate_payload, check_final_metadata


def write_response(path, raw, corrected, response, panel, spec, cfg):
    """Construct the approved response once; validator derives its own expectations."""
    require(corrected.shape == response.shape == (300, len(raw["cells"])), "Missing all-cell output genes")
    blocks = [np.flatnonzero(raw["metadata"]["cluster_coarse"] == label) for label in ("Mic", "AST", "OGC")]
    sizes = np.array([len(x) for x in blocks], dtype=np.int64)
    require(np.all(sizes > 0), "Missing modeled type")
    cells = np.concatenate(blocks)
    genes = np.array(panel["raw_300_positions_zero_based"], dtype=np.int64)
    types = np.repeat(np.arange(3, dtype=np.int64), sizes)
    selected = response[np.ix_(genes, cells)]
    means = np.column_stack([selected[:, types == t].mean(axis=1, dtype=np.float64) for t in range(3)])
    values = {"/axes/genes300/ids":raw["genes"], "/axes/genes300/raw_gene_index":np.arange(300),
        "/axes/genes91/ids":panel["genes"], "/axes/genes91/raw_gene_index":genes,
        "/axes/genes91/all_gene_index":genes,
        "/axes/cells_all/ids":raw["cells"], "/axes/cells_all/source_row":raw["rows"],
        "/axes/cells_model/ids":raw["cells"][cells], "/axes/cells_model/source_row":raw["rows"][cells],
        "/axes/cells_model/all_cell_index":cells,
        "/axes/types/labels":["MIC","AST","OGC"], "/axes/types/codes":[0,1,2],
        "/axes/coordinates/labels":["center_y","center_x"],
        "/all/corrected_counts":corrected, "/all/log1p_response":response,
        "/model/uncentered_response":selected, "/model/centered_response":selected-means[:,types],
        "/centering/means":means, "/centering/group_sizes":sizes,
        "/metadata/model_type_code":types, "/coordinates/all_source":raw["coordinates"],
        "/coordinates/model_source":raw["coordinates"][cells]}
    values.update({"/metadata/all/"+k: raw["metadata"][k] for k in META})
    with h5py.File(path, "x") as f:
        f.attrs["schema"] = spec["bundle_schema"]
        f.attrs["coordinates_contract"] = json.dumps(spec["coordinates"], sort_keys=True)
        for name, rule in spec["datasets"].items():
            dtype = {"float64":"<f8", "int64":"<i8", "utf8":h5py.string_dtype("utf-8")}[rule["dtype"]]
            d = f.create_dataset(name, data=np.asarray(values[name], dtype=dtype), dtype=dtype,
                compression=cfg["storage"]["compression"], compression_opts=cfg["storage"]["compression_opts"],
                shuffle=cfg["storage"]["shuffle"] if rule["dtype"] != "utf8" else False)
            d.attrs["axis_refs"] = json.dumps([AXES[a] for a in rule["axes"]])
            d.attrs["axis_hashes"] = json.dumps([ordered_hash(values[AXES[a]]) for a in rule["axes"]])
        f.flush()
    with path.open("r+b") as stream:
        os.fsync(stream.fileno())
    with h5py.File(path, "r") as f:
        physical = {name:{"chunks":list(f[name].chunks), "compression":f[name].compression,
                          "compression_opts":f[name].compression_opts, "shuffle":bool(f[name].shuffle)}
                    for name in spec["datasets"]}
    return physical


def promote(attempt_bundle, destination):
    require(not destination.exists(), "Refusing to overwrite finalized section")
    require((attempt_bundle / "manifest.json").is_file(), "No final manifest; promotion forbidden")
    from .response_contract import load_json
    _, _, spec, _ = contract()
    manifest = load_json(attempt_bundle / "manifest.json")
    require(destination.name == manifest["section"], "Promotion section mismatch")
    check_final_metadata(attempt_bundle, manifest, load_json(attempt_bundle / "validation.json"), spec)
    require(attempt_bundle.stat().st_dev == destination.parent.stat().st_dev, "Cross-filesystem promotion forbidden")
    attempt_bundle.rename(destination)


def run(section, source, envroot, config, destination_root):
    started = time.monotonic()
    cfg, panel, spec, registry = contract(config)
    require(section in [s["section"] for s in registry["sections"]], "Unknown registered section")
    root = destination_root.resolve()
    require(not root.is_relative_to(REPO), "Bundles must stay outside Git")
    require(not root.exists(), "Fresh destination root required; existing sections are never overwritten")
    expected_identities = identities(config, envroot)
    code = code_identity()
    root.mkdir(parents=True, exist_ok=False)
    attempt = root / ('.attempt-'+uuid.uuid4().hex)
    bundle = attempt / 'bundle'
    bundle.mkdir(parents=True)
    save_json(attempt / 'attempt.json', {"state":"writing", "section":section, "code":code, "identities":expected_identities})
    try:
        raw = raw_section(source, section, config)
        write_input(attempt / 'input', raw["counts"], raw["genes"], raw["cells"], raw["source"])
        normalization = run_r(envroot, attempt / 'input', attempt / 'normalization', cfg["normalization"]["depth"],
                              timeout=cfg["limits"]["seconds"], memory_limit=cfg["limits"]["working_set_bytes"])
        transported, transport = readback(envroot, raw, attempt / 'normalization/fit.rds', attempt / 'transport', 124)
        require(transport["report"]["semantic_sha256"] == normalization["report"]["semantic_sha256"], "Transport changed logical values")
        shutil.copyfile(attempt / 'normalization/fit.rds', bundle / 'fit.rds')
        shutil.copyfile(attempt / 'normalization/session.txt', bundle / 'session.txt')
        physical = write_response(bundle / 'response.h5', raw, transported["corrected"], transported["response"], panel, spec, cfg)
        execution = {"schema":"bsfm.single-section-execution.v1", "section":section,
            "source":raw["source"], "code":code, "identities":expected_identities,
            "run_configuration":cfg, "environment_root":str(envroot.resolve()),
            "command":[sys.executable,*sys.argv], "normalization":normalization,
            "transport_readback":transport, "physical_storage":physical,
            "pre_validation_elapsed_seconds":time.monotonic()-started}
        save_json(bundle / 'execution.json', execution)
        for name in ('fit.rds','session.txt'):
            with (bundle/name).open('r+b') as stream:
                os.fsync(stream.fileno())
        report = validate_payload(bundle, source, envroot, config, attempt / 'independent-validation')
        save_json(bundle / 'validation.json', report)
        manifest = {"schema":spec["bundle_schema"], "status":"complete",
            **{k:report[k] for k in ('section','animal_label','genotype','source','identities','code_commit','dimensions','axes','datasets')},
            "regime":spec["regime"], "coordinates":spec["coordinates"], "validation":report["metrics"],
            "artifacts":{name:file_record(bundle/name) for name in spec["required_files"]}}
        save_json(bundle / 'manifest.json', manifest)
        check_final_metadata(bundle, manifest, report, spec)
        require(code_identity() == code and identities(config, envroot) == expected_identities, "Producer identities changed during run")
        destination = root / section
        promote(bundle, destination)
        receipt = {"schema":"bsfm.section-promotion.v1", "section":section,
            "manifest":file_record(destination/'manifest.json'), "bundle":str(destination),
            "elapsed_seconds":time.monotonic()-started, "metrics":report["metrics"],
            "normalization_peak_working_set_bytes":normalization["process"]["peak_working_set_bytes"]}
        save_json(root/'promotion.json', receipt)
        return receipt
    except Exception as exc:
        save_json(attempt/'failure.json', {"state":"failed", "error":str(exc), "section":section})
        raise


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--section', required=True)
    p.add_argument('--raw-source', type=Path, required=True)
    p.add_argument('--environment', type=Path, required=True)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--destination-root', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(run(a.section, a.raw_source.resolve(), a.environment.resolve(), a.config.resolve(), a.destination_root)))


if __name__ == '__main__':
    main()
