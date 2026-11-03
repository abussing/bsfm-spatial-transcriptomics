"""Authenticated small real-data derivative; not canonical full-cell validation."""
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.contracts import ModelInput, input_identity, logical_hash
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.run_chart import geometry_from_genesis
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_inputs import authenticate_environment, authenticate_files, load_inputs
from bsfm.sampler.run_storage import file_record, read_json, write_json
from bsfm.sampler.warp import WarpGeometry, mesh_identity
from smoke_rule import load_smoke_rule

REPO = Path(__file__).resolve().parents[3]
MIRROR = Path('/work/abussing/bsfm-consolidation/canonical-artifacts-20261103')


def selected_rows(codes, types, per_type=8):
    """Evenly spaced indices within each ordered type; no response-based selection."""
    if type(per_type) is not int or per_type < 2:
        raise ValueError('At least two cells per type required')
    rows = []
    for code in range(types):
        candidates = np.flatnonzero(codes == code)
        if len(candidates) < per_type:
            raise ValueError('Insufficient cells for declared subset')
        rows.extend(candidates[np.linspace(0, len(candidates)-1, per_type, dtype=int)].tolist())
    return np.asarray(rows, dtype=np.int64)


def runtime_files():
    registration = REPO/'docs/initialization/audits/S10_fullcell_v2_20261103/receipt.json'
    r = read_json(registration)
    expected = {
        'prepared': ('s10-preparation-v2/prepared/model-input.npz', r['prepared_npz']),
        'contract': ('s10-preparation-v2/prepared/input-contract.json', r['prepared_contract']),
        'mesh': ('s10-mesh/sampler-facing.npz', r['upstream']['mesh']),
        'gpinit': ('s10-preparation-v2/gpinit-run1/gpinit.npz', r['fits'][0]['output']),
        'certificate': ('s10-preparation-v2/gpinit-run1/certificate.json', r['fits'][0]['certificate']),
        'response_manifest': ('sct-v2/sections/S10__WT5/manifest.json', r['upstream']['response_manifest']),
        'response_validation': ('sct-v2/sections/S10__WT5/validation.json', r['upstream']['validation'])}
    files = {name: dict(path=str(MIRROR/relative), bytes=record['bytes'], sha256=record['sha256'])
             for name, (relative, record) in expected.items()}
    files['registration'] = dict(path=str(registration), **file_record(registration))
    return files


def subset(parent, loading, eta, genesis):
    data = parent.inputs.arrays
    rows = selected_rows(data['cell_id'], len(data['cell_type_names']))
    arrays = {k: np.array(v, copy=True) for k, v in data.items()}
    arrays['Y'] = arrays['Y'][:, rows].copy()
    for name in ('slocs', 'cell_id', 'cell_names', 'source_row_indices'):
        arrays[name] = arrays[name][rows].copy()
    identity = json.loads(parent.inputs.identity_json)
    inputs = ModelInput.authenticate(arrays, input_identity(arrays, section=identity['section'],
        response_sha256=identity['response_sha256'], coordinate_system=identity['coordinate_system']))
    geometry = {k: np.array(v, copy=True) for k, v in parent.geometry.arrays.items()}
    for name in ('projector', 'locations', 'cell_ids', 'source_rows'):
        geometry[name] = geometry[name][rows].copy()
    geometry['active_indices'] = np.flatnonzero(np.any(geometry['projector'] != 0, axis=0))
    original = json.loads(parent.geometry.identity_json)
    expected = mesh_identity(geometry, section=original['section'], mesh_sha256=original['mesh_sha256'])
    geo = geometry_from_genesis(geometry, expected, genesis) if genesis.exists() else WarpGeometry.authenticate(geometry, expected)
    target = DirectWTarget(inputs, geo, load_smoke_rule(), factor_ids=parent.factor_ids[:2])
    seeds = (loading[:, :, :2].copy(), eta[:2, rows].copy())
    selection = dict(parent_row_indices=rows.tolist(), source_row_indices=arrays['source_row_indices'].tolist(),
        cell_names=arrays['cell_names'].tolist(), factor_indices=[0, 1], cells=len(rows), factors=2,
        genes=len(arrays['gene_names']), full_modes=len(geometry['vertices']),
        smoke_rule_order=json.loads(target.rule.identity_json)['order'],
        frequency_nodes=len(target.rule.arrays['omega']), feature_columns=2*len(target.rule.arrays['omega']),
        active_vertices=len(geometry['active_indices']), response_recentered=False,
        gpinit_refitted=False, mesh_regenerated=False, primary_holdout_scoring_eligible=False,
        loading_sha256=logical_hash(seeds[0]), eta_sha256=logical_hash(seeds[1]))
    if selection['cells'] != 24 or selection['genes'] != 91 or selection['full_modes'] != 371:
        raise ValueError('Unexpected S10 derivative dimensions')
    return target, seeds, selection


def main(commit, output, phase):
    output = Path(output)
    if phase not in ('first', 'resume', 'nonreplay'):
        raise ValueError('Unknown smoke phase')
    def clean():
        if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip() != commit:
            raise ValueError('Wrong generating commit')
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=REPO, text=True).strip():
            raise ValueError('Dirty source checkout')
    clean()
    environment = authenticate_environment()
    files = runtime_files()
    parent, loading, eta, parent_binding = load_inputs(files, tuple(f'factor-{i:03d}' for i in range(1, 21)))
    run = output/'run'
    genesis = run/'segments/segment/genesis/endpoint.npz'
    if phase == 'first' and run.exists():
        raise ValueError('Fresh smoke root required')
    if phase != 'first' and not genesis.exists():
        raise ValueError('Resume requires retained genesis')
    target, seeds, selection = subset(parent, loading, eta, genesis)
    binding = dict(schema='bsfm.s10-subset-smoke-input.v1', files=files,
        parent_preparation_commit=parent_binding['preparation_commit'], selection=selection,
        target_identity=target.identity, spectral_identity=target.geometry.spectral_identity,
        scope='24-cell two-factor L4 full-data derivative; execution check only; not L16 validation or held-out prediction')
    spec = dict(schema='bsfm.local-run.v1', run_id='s10_subset_smoke', segment_id='segment', chain_id='chain',
        factor_ids=list(target.factor_ids), seed=20261103, warmup_steps=20, settling_sweeps=0,
        production_sweeps=2, final_sweep=2, save_every=1, checkpoint_every=1,
        mode='exact_resume', input_sha256=digest(binding))
    spec['software'] = dict(git_commit=commit, clean_tree=True, run_config_sha256=digest(spec),
        environment_lock_sha256=environment['lock']['sha256'], environment_identity=digest(environment))
    for name, value in [('input-binding.json', binding), ('run-spec.json', spec), ('environment.json', environment)]:
        path = output/name
        if phase == 'first':
            write_json(path, value)
        elif read_json(path) != value:
            raise ValueError('Resume changed '+name)
    def authenticate():
        clean()
        authenticate_files(files)
        target._validate_identities()
        if authenticate_environment() != environment:
            raise ValueError('Environment changed')
        if logical_hash(seeds[0]) != selection['loading_sha256'] or logical_hash(seeds[1]) != selection['eta_sha256']:
            raise ValueError('Derived seeds changed')
    controller = RunController(run, target, *seeds, spec, binding, authenticate=authenticate)
    if phase == 'nonreplay':
        def forbidden(*args, **kwargs):
            raise AssertionError('Completed smoke attempted another sweep')
        controller.layer.sweep = forbidden
    result = controller.run(stop_after=1 if phase == 'first' else None)
    if result['completed'] != (1 if phase == 'first' else 2):
        raise AssertionError('Unexpected completed sweep count')
    if phase == 'nonreplay' and result != read_json(output/'resume.json'):
        raise AssertionError('Completion changed on non-replay')
    write_json(output/(phase+'.json'), result)
    print(phase, result['status'], result['completed'], flush=True)


if __name__ == '__main__':
    main(*sys.argv[1:])
