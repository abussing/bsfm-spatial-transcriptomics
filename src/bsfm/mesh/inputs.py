"""Authenticate canonical provenance before opening any scientific dataset."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
from concurrent.futures import ThreadPoolExecutor
import h5py
import numpy as np
from .identities import require,sha,read_json,ordered_ids,REPO

RUN_HASH='03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f'
REGISTRY_HASH='f336de10e58e0b2269ceed62c4c6c454af9956f9460c9097b3d42c7ccf368166'


def environment(root,*,full=True):
    root=Path(root).resolve();runtime=read_json(REPO/'environment/mesh/runtime-lock.json')
    for rec in [runtime['R'],runtime['python_base'],runtime['python_venv']]+runtime['python_base_companions']:
        require(sha(rec['path'])==rec['sha256'],'Runtime identity mismatch')
    import sys
    require(Path(sys.prefix).resolve()==root/'python','Wrong mesh Python environment')
    for rec in read_json(REPO/'environment/mesh/python-source-lock.json')['wheels']:
        require(importlib.metadata.version(rec['package'])==rec['version'],'Python dependency version mismatch')
        installed=Path(importlib.metadata.distribution(rec['package']).locate_file('')).resolve()
        require(installed.is_relative_to(root/'python'),'Python library fallback')
    installed=read_json(REPO/'docs/environment/evidence/mesh-phase0-20261031/installed-integrity.json')
    for package in installed['r_packages']:
        for rec in package['metadata']:require(sha(rec['path'])==rec['sha256'],'R package metadata mismatch')
    anchors=read_json(REPO/'docs/environment/evidence/mesh-phase0-restore-check-20261031/immutability.json')['roots']
    anchor=anchors[0];r_anchor=anchors[1]
    require(Path(r_anchor['root']).resolve()==Path(runtime['R_tree']['root']).resolve(),'R tree anchor path')
    digest=None;r_digest=None
    if full:
        def tree_digest(directory):
            paths=sorted(p for p in directory.rglob('*') if p.is_file())
            def record(p):return dict(relative=p.relative_to(directory).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
            with ThreadPoolExecutor(max_workers=8) as pool:rows=list(pool.map(record,paths))
            rows.sort(key=lambda x:x['relative'])
            return hashlib.sha256((json.dumps(rows,sort_keys=True,separators=(',',':'))+'\n').encode()).hexdigest()
        digest=tree_digest(root)
        require(digest==anchor['sha256'],'Frozen environment tree changed')
        r_digest=tree_digest(Path(runtime['R_tree']['root']))
        # The restoration receipt uses this canonical sorted-record encoding;
        # runtime-lock's earlier tree hash uses a different inventory encoding.
        require(r_digest==r_anchor['sha256'],'Shared immutable R runtime changed')
    return dict(root=str(root),expected_tree_sha256=anchor['sha256'],measured_tree_sha256=digest,
        full=full,R_tree_sha256=r_digest,runtime_lock_sha256=sha(REPO/'environment/mesh/runtime-lock.json'))


def code(expected_commit=None,*,real=False):
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    if expected_commit is not None:require(commit==expected_commit,'Generating commit mismatch')
    if real:
        require(expected_commit is not None,'Real run requires explicit generating commit')
        require(not subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip(),'Real run requires clean committed code')
    files=sorted(Path(__file__).parent.glob('*.py'))+sorted(Path(__file__).parent.glob('*.R'))
    return dict(commit=commit,real_committed_run=real,files={p.relative_to(REPO).as_posix():sha(p) for p in files})


def load_bundle(path,manifest,*,expected_section=None):
    """Called only after the parent's manifest hash is authenticated."""
    path=Path(path);require(manifest['status']=='complete','Incomplete response bundle')
    if expected_section:require(manifest['section']==expected_section,'Section mismatch')
    record=manifest['artifacts']['response.h5'];response=path/'response.h5'
    require(record['path']=='response.h5' and response.stat().st_size==record['bytes'] and sha(response)==record['sha256'],'Response file authentication')
    require(manifest['coordinates']['axis_order']==['center_y','center_x'] and manifest['coordinates']['units']=='source_native','Coordinate contract')
    result={}
    # Identity axes are authenticated before opening the coordinate datasets.
    datasets={'all_ids':'/axes/cells_all/ids','model_ids':'/axes/cells_model/ids',
        'all_rows':'/axes/cells_all/source_row','model_rows':'/axes/cells_model/source_row',
        'model_index':'/axes/cells_model/all_cell_index','types':'/metadata/model_type_code',
        'axis_order':'/axes/coordinates/labels','all_xy':'/coordinates/all_source','model_xy':'/coordinates/model_source'}
    with h5py.File(response,'r') as f:
        for key,name in datasets.items():
            record=manifest['datasets'][name];ds=f[name]
            require(list(ds.shape)==record['shape'],'Dataset dimensions mismatch')
            if record['dtype']=='utf8':
                values=ds.asstr()[:];digest=ordered_ids(values)
            else:
                require(record['dtype'] in ['float64','int64'],'Unsupported canonical dtype')
                dt=np.dtype('<f8' if record['dtype']=='float64' else '<i8')
                require(ds.dtype==dt,'Coordinate/identity dtype mismatch')
                values=ds[:];digest=hashlib.sha256(np.asarray(values,dtype=dt).tobytes()).hexdigest()
            require(digest==record['semantic_sha256'],'Dataset logical identity mismatch: '+name)
            result[key]=values
    validate_population(result,manifest['dimensions'])
    return result


def validate_population(x,dimensions):
    n=dimensions['all_cells'];m=dimensions['model_cells'];idx=x['model_index']
    require(x['all_xy'].shape==(n,2) and x['model_xy'].shape==(m,2),'Population dimensions')
    require(x['axis_order'].tolist()==['center_y','center_x'],'Coordinate axes/order')
    require(np.isfinite(x['all_xy']).all() and np.isfinite(x['model_xy']).all(),'Nonfinite coordinates')
    require(len(np.unique(x['all_ids']))==n and len(np.unique(x['all_rows']))==n,'Nonunique all-cell identities')
    require(np.all(np.diff(x['all_rows'])>0),'All-cell row order')
    require(idx.dtype.kind in 'iu' and len(idx)==m and len(np.unique(idx))==m and idx.min()>=0 and idx.max()<n,'Model membership')
    for allkey,modelkey in [('all_ids','model_ids'),('all_rows','model_rows'),('all_xy','model_xy')]:
        require(np.array_equal(x[allkey][idx],x[modelkey]),'Identity-based coordinate/membership mismatch')
    require(np.array_equal(np.unique(x['types']),[0,1,2]),'Model types incomplete')
    order=np.lexsort((x['model_rows'],x['types']))
    require(np.array_equal(order,np.arange(m)),'Canonical modeled-cell order')


def real_inputs(run_root,section,envroot,expected_commit):
    identity=code(expected_commit,real=True);env=environment(envroot)
    study_path=REPO/'config/mesh/study-design.json';study=read_json(study_path)
    registry_path=REPO/'src/bsfm/preprocessing/sections.json'
    require(sha(registry_path)==REGISTRY_HASH==study['registry']['sha256'],'Registry identity')
    receipt=REPO/'docs/preprocessing/audits/20261031_production_v2/run-manifest.json'
    require(sha(receipt)==RUN_HASH and sha(Path(run_root)/'run-manifest.json')==RUN_HASH,'Production receipt/run manifest')
    rm=read_json(receipt);require(rm['status']=='complete' and rm['pass'],'Incomplete production')
    require(section in rm['section_order'],'Unknown canonical section')
    entry=next(x for x in rm['sections'] if x['section']==section)['manifest']
    manifest_path=Path(run_root)/entry['path']
    require(manifest_path.resolve().is_relative_to(Path(run_root).resolve()),'Unsafe section path')
    require(manifest_path.stat().st_size==entry['bytes'] and sha(manifest_path)==entry['sha256'],'Section manifest identity')
    manifest=read_json(manifest_path)
    require(manifest['identities']['section_registry_sha256']==REGISTRY_HASH,'Section registry mismatch')
    require(manifest['code_commit']==rm['code']['commit'],'Response generating commit mismatch')
    data=load_bundle(manifest_path.parent,manifest,expected_section=section)
    provenance=dict(code=identity,environment=env,study_sha256=sha(study_path),run_manifest_sha256=RUN_HASH,
        section_manifest_sha256=entry['sha256'],registry_sha256=REGISTRY_HASH,section=section,
        source=manifest['source'],dimensions=manifest['dimensions'],regime=manifest['regime'])
    return data,provenance
