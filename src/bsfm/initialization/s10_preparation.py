"""Bounded full-cell S10 preparation gate; no normalization, GP fit or sampler.

The existing response/mesh and their accepted identities are read-only. All
preconditions pass in memory before a fresh output directory is created.
"""
import argparse
import json
from pathlib import Path
import subprocess

from .preparation_environment import REPO, authenticate, record, require, sha

SECTION = 'S10__WT5'
PRODUCER = '6eb672bebbaf5cde6c9d50391aac275a210832a6'
RUN_HASH = '03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f'
MESH_HASH = '69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0'
MANIFEST_HASH = '40e2028f2aeff0cec2e9ba3a23b748702da65947d4637db304a136e52599ff13'
RAW_HASH = 'd6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38'
COUNTS = [996, 3337, 5089]
KEYS = ('Y','slocs','cell_id','cell_names','source_row_indices','gene_names','cell_type_names')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def identities(data):
    from bsfm.sampler.contracts import logical_hash
    return {name: logical_hash(data[name]) for name in KEYS}


def validate_model(data, expected, genes):
    import numpy as np
    require(set(data) == set(KEYS), 'Exactly seven model-input arrays required')
    require(data['Y'].shape == (91,9422), 'Canonical full-cell S10 requires Y[91,9422]')
    require(data['Y'].dtype == np.float64 and np.isfinite(data['Y']).all(), 'Invalid response')
    require(data['slocs'].shape == (9422,2) and data['slocs'].dtype == np.float64
            and np.isfinite(data['slocs']).all(), 'Invalid locations')
    require(np.array_equal(data['cell_type_names'], ['MIC','AST','OGC']), 'Type mapping')
    require(np.array_equal(data['cell_id'], np.repeat(np.arange(3), COUNTS)), 'Type block order')
    require(np.array_equal(data['gene_names'], genes), 'Ordered panel mismatch')
    for name,length in [('cell_names',9422),('gene_names',91),('cell_type_names',3)]:
        require(data[name].dtype.kind == 'U' and data[name].shape == (length,)
                and len(np.unique(data[name])) == len(data[name]) and np.all(data[name] != ''),
                'Invalid string identity: '+name)
    rows = data['source_row_indices']
    require(rows.shape == (9422,) and rows.dtype == np.int64 and np.all(rows >= 0)
            and len(np.unique(rows)) == 9422, 'Invalid source rows')
    for code in range(3):
        require(np.all(np.diff(rows[data['cell_id'] == code]) > 0), 'Source row order')
    require(identities(data) == expected, 'Exact array/value/order mismatch')


def check_join(data, coordinates, mesh):
    import numpy as np
    from bsfm.mesh.october26 import normalize_glia
    norm, origin, scale = normalize_glia(coordinates)
    require(np.array_equal(norm, data['slocs']), 'Coordinate transformation mismatch')
    for a,b in [('slocs','slocs'),('source_rows','source_row_indices'),('cell_type','cell_id')]:
        require(np.array_equal(mesh[a], data[b]), 'Mesh/model order mismatch: '+a)
    require(mesh['mesh_vertices'].shape == (371,2) and mesh['triangles'].shape == (708,3), 'S10 mesh dimensions')
    require(mesh['A_full'].shape == (9422,371), 'Full projector population')
    active = np.flatnonzero(np.any(mesh['A_full'] != 0, axis=0))
    require(len(active) == 168 and np.array_equal(active, mesh['active_indices_full']), 'Full active support')
    require(np.array_equal(mesh['A_active'], mesh['A_full'][:,active]), 'Active projector changed')
    require(np.array_equal(mesh['inactive_indices_full'], np.setdiff1d(np.arange(371), active)), 'Inactive partition')
    require(mesh['spectral_U'].shape == (371,371)
            and mesh['modal_diagonals'].shape == (7,371), 'All 371 modes required')
    require(all(mesh[n].shape == (371,371) for n in ['fem_C']+[f'fem_g{i}' for i in range(1,7)]), 'FEM shape')
    require(np.isfinite(mesh['A_full']).all() and np.min(mesh['A_full']) >= -2e-10, 'Projector weights')
    row_error = float(np.max(abs(mesh['A_full'].sum(axis=1)-1)))
    affine_error = float(np.max(abs(mesh['A_full']@mesh['mesh_vertices']-norm)))
    require(row_error < 2e-10 and affine_error < 2e-10, 'Accepted projector tolerance')
    return dict(status='pass', cells=9422, types=COUNTS, vertices=371, triangles=708,
                active_vertices=168, inactive_vertices=203, modes=371,
                source_rows_equal=True, type_order_equal=True, locations_equal=True,
                maximum_location_error=0.0, projector_row_sum_error=row_error,
                affine_reconstruction_error=affine_error, historical_subset_used=False,
                origin=origin.tolist(), scale=scale)


def prepare_checks(production, mesh_path, raw, r_environment):
    import h5py
    import numpy as np
    from bsfm.preprocessing.response_contract import contract, inventory
    from bsfm.preprocessing.response_validate import check_final_metadata
    from bsfm.preprocessing.execution_evidence import authenticate_process
    from bsfm.preprocessing.raw_preflight import axis_ids, strings
    from bsfm.mesh.october26 import normalize_glia
    from bsfm.mesh.identities import logical
    cfg, panel, spec, registry = contract()
    require(sha(production/'run-manifest.json') == RUN_HASH, 'Production run identity')
    run_spec = read_json(production/'run-specification.json')
    require(run_spec == read_json(REPO/'docs/preprocessing/audits/20261031_production_v2/run-specification.json'), 'Production specification')
    bundle = production/'sections'/SECTION
    require(sha(bundle/'manifest.json') == MANIFEST_HASH, 'S10 manifest identity')
    m = read_json(bundle/'manifest.json'); v = read_json(bundle/'validation.json')
    check_final_metadata(bundle,m,v,spec)
    require(m['code_commit'] == PRODUCER and m['section'] == SECTION, 'Response producer/section')
    require(v['status'] == 'pass' and v['metrics']['all_invariants_passed']
            and v['metrics']['readback_passed'], 'Original deep validation')
    ex = read_json(bundle/'execution.json')
    require(ex['production_run_spec_sha256'] == sha(production/'run-specification.json'), 'Execution/run identity')
    require(ex['code'] == run_spec['code'], 'Execution code identity')
    for path,digest in run_spec['code']['source_files'].items():
        import hashlib
        blob = subprocess.check_output(['git','show',PRODUCER+':'+path],cwd=REPO)
        require(hashlib.sha256(blob).hexdigest() == digest, 'Historical committed response source')
    for name,expected in run_spec['single_section_configuration']['environment_files'].items():
        require(sha(r_environment/name) == expected, 'SCT environment source lock')
    for phase in ('normalization','transport_readback'):
        authenticate_process(ex[phase]['process'])
    require(v['independent_readback']['report']['semantic_sha256'] == ex['normalization']['report']['semantic_sha256'], 'Deep semantic readback')
    raw_identity = record(raw)
    require(raw_identity['sha256'] == RAW_HASH and raw_identity['bytes'] == m['source']['bytes'], 'Raw source fingerprint')
    with h5py.File(bundle/'response.h5','r') as f:
        ds, axes = inventory(f,spec)
        require(ds == m['datasets'] and axes == m['axes'], 'Response dataset identities')
        require(f['axes/coordinates/labels'].asstr()[:].tolist() == ['center_y','center_x'], 'Coordinate axes')
        coords = f['coordinates/model_source'][:]
        norm,origin,scale = normalize_glia(coords)
        data = dict(Y=f['model/centered_response'][:], slocs=norm,
                    cell_id=f['metadata/model_type_code'][:],
                    source_row_indices=f['axes/cells_model/source_row'][:])
        for name,path in [('cell_names','axes/cells_model/ids'),('gene_names','axes/genes91/ids'),('cell_type_names','axes/types/labels')]:
            data[name] = np.asarray(f[path].asstr()[:], dtype=str)
    validate_model(data,identities(data),panel['genes'])
    selector = next(s for s in registry['sections'] if s['section'] == SECTION)
    with h5py.File(raw,'r') as f:
        cells,_ = axis_ids(f['obs']); genes,_ = axis_ids(f['var'])
        sample = strings(f['obs/sample']); fine = strings(f['obs/gen_fine'])
        labels = strings(f['obs/cluster_coarse'])
        section_mask = (sample == selector['sample']) & (fine == selector['gen_fine'])
        raw_rows = np.concatenate([np.flatnonzero(section_mask & (labels == s)) for s in ('Mic','AST','OGC')])
        require(np.array_equal(raw_rows,data['source_row_indices']), 'Raw global row/population join')
        require(np.array_equal(cells[raw_rows],data['cell_names']), 'Original raw cell identity join')
        require(np.array_equal(genes[panel['raw_300_positions_zero_based']],data['gene_names']), 'Raw gene/panel join')
        # h5py indexed reads require sorted indices; invert this read permutation
        # explicitly without changing the canonical model order.
        order = np.argsort(raw_rows); inv = np.argsort(order)
        raw_xy = f['obsm/spatial'][raw_rows[order]][inv]
        require(np.array_equal(coords,raw_xy), 'Unchanged source-native coordinates')
        for j,name in enumerate(('center_y','center_x')):
            require(np.array_equal(raw_xy[:,j],f['obs/'+name][raw_rows[order]][inv]), 'Raw coordinate columns')
        raw_labels = {name: np.unique(strings(f['obs/'+name])[raw_rows]).tolist() for name in ('gen','gen_coarse')}
    require(sha(mesh_path) == MESH_HASH, 'Accepted mesh file identity')
    mesh_receipt_path = REPO/'docs/mesh/audits/october26_S10_localization_20261102/corrected-reproduction.json'
    mr = read_json(mesh_receipt_path)
    with np.load(mesh_path,allow_pickle=False) as z:
        mesh = {k:z[k].copy() for k in z.files}
    inv = mr
    require(mr['status'] == 'PASS' and mr['output']['sha256'] == MESH_HASH, 'Mesh receipt')
    for name,a in mesh.items():
        require(logical(a) == inv['arrays'][name]['sha256'], 'Mesh logical identity: '+name)
    join = check_join(data,coords,mesh)
    binding = dict(response_manifest=record(bundle/'manifest.json'), validation=record(bundle/'validation.json'),
                   response_h5=record(bundle/'response.h5'), response_producer_commit=PRODUCER,
                   production_manifest=record(production/'run-manifest.json'), raw_source=raw_identity,
                   registry=record(REPO/'src/bsfm/preprocessing/sections.json'),
                   panel=record(REPO/'config/preprocessing/modeling-panel.json'),
                   mesh=record(mesh_path), mesh_receipt=record(mesh_receipt_path),
                   mesh_arrays=inv['arrays'], metadata=raw_labels,
                   coordinate_transform=dict(formula='(source_coordinates-origin)/scale',
                       origin=origin.tolist(),scale=scale,axes=['center_y','center_x'],
                       source_units='source_native',geometry_population='all 9422 modeled glial cells'),
                   join=join, response_transformation='none; exact final_centered_Y copy',
                   preprocessing_regime='full_data',primary_holdout_scoring_eligible=False)
    return data,binding


def reopen(output, expected, genes):
    import numpy as np
    c = read_json(output/'input-contract.json')
    require(c['schema'] == 'bsfm.gpinit-input.v1' and c['response'] == 'final_centered_Y', 'Contract schema')
    require(c['source_sha256'] == sha(output/'model-input.npz'), 'Prepared NPZ identity')
    with np.load(output/'model-input.npz',allow_pickle=False) as z:
        data = {name:z[name].copy() for name in z.files}
    require(c['arrays'] == expected, 'Contract changed')
    validate_model(data,expected,genes)
    return dict(status='pass', arrays=expected, npz=record(output/'model-input.npz'),contract=record(output/'input-contract.json'))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('production','mesh','raw','r-environment','output'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--validate-only',action='store_true')
    args = p.parse_args()
    env = authenticate('preparation')
    data,binding = prepare_checks(args.production,args.mesh,args.raw,args.r_environment)
    if args.validate_only:
        result = reopen(args.output,identities(data),data['gene_names'])
        require(read_json(args.output/'input-contract.json')['upstream'] == binding,'Upstream binding changed')
        print(json.dumps(result,indent=2)); return
    require(not args.output.exists(),'Fresh external output required')
    require(not args.output.resolve().is_relative_to(REPO),'Prepared data must remain outside Git')
    import numpy as np
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    dirty = bool(subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip())
    args.output.mkdir(parents=True,exist_ok=False)
    with (args.output/'model-input.npz').open('xb') as stream:
        np.savez_compressed(stream,**data)
    producer = dict(baseline_commit=commit,worktree_clean=not dirty,
                    generating_commit=None if dirty else commit,
                    status='uncommitted_preparation_review_evidence' if dirty else 'committed_preparation',
                    source_files=[record(__file__),record(Path(__file__).with_name('preparation_environment.py'))])
    c = dict(schema='bsfm.gpinit-input.v1',response='final_centered_Y',section=SECTION,
             source_sha256=sha(args.output/'model-input.npz'),arrays=identities(data),
             upstream=binding,producer=producer,environment=env,
             scope='mechanical full-cell S10 validation; K=20 is not a production choice',
             gpinit_gate=dict(factors=20,nfit=250,seed=2026102610))
    write_json(args.output/'input-contract.json',c)
    write_json(args.output/'preparation-validation.json',reopen(args.output,c['arrays'],data['gene_names']))
    print(json.dumps(dict(status='pass',output=str(args.output),join=binding['join']),indent=2))


if __name__ == '__main__':
    main()
