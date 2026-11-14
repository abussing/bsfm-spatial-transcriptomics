"""Authenticated NPZ-only runtime entry. No h5py, R, sklearn or helper interpreter."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import os
from pathlib import Path, PureWindowsPath
import site
import subprocess
import sys
import zipfile
import numpy as np
import jax
from threadpoolctl import threadpool_info
from .contracts import ModelInput, input_identity, logical_hash, array
from .warp import WarpGeometry, mesh_identity
from .field_target import DirectWTarget
from .rule import load_rule
from .checkpoint_contract import digest
from .run_storage import file_record, read_json

REPO=Path(__file__).resolve().parents[3]


def authenticate_environment(*, gpu_runtime=None):
    if gpu_runtime is not None:
        if 'schema' in gpu_runtime:
            from .run_validated_gpu_environment import authenticate_validated_gpu_environment
            return authenticate_validated_gpu_environment(**gpu_runtime)
        from .run_gpu_environment import authenticate_gpu_environment
        return authenticate_gpu_environment(**gpu_runtime)
    if sys.platform=='linux':
        from .run_linux_environment import authenticate_linux_environment
        return authenticate_linux_environment()
    lockpath=REPO/'environment/sampler-layer5/source-lock.json';lock=read_json(lockpath)
    prefix=Path(sys.prefix).resolve();root=prefix.parent
    if (sys.version.split()[0]!=lock['python'] or site.ENABLE_USER_SITE or sys.prefix==sys.base_prefix
        or os.name!='nt' or jax.default_backend()!='cpu' or not jax.config.x64_enabled
        or 'include-system-site-packages = false' not in (prefix/'pyvenv.cfg').read_text()):
        raise ValueError('Accepted isolated Windows CPU/x64 environment required')
    norm=lambda s:s.lower().replace('_','-')
    distributions=list(metadata.distributions());actual={norm(d.metadata['Name']):d.version for d in distributions}
    expected={'pip':lock['pip'],**{norm(p['name']):p['version'] for p in lock['packages']}}
    if actual!=expected or len(distributions)!=len(expected):raise ValueError('Environment closure mismatch')
    runtime=[]
    for r in lock['runtime']:
        p=Path(sys.base_prefix)/PureWindowsPath(r['path']).name
        if file_record(p)!={k:r[k] for k in ('bytes','sha256')}:raise ValueError('Runtime changed')
        runtime.append(dict(path=str(p.resolve()),**file_record(p)))
    installed=read_json(root/'installed.json')
    for filename,field in [('source-lock.json','lock_sha256'),('requirements.lock.txt','requirements_sha256')]:
        data=(lockpath.parent/filename).read_bytes()
        if installed[field] not in [hashlib.sha256(x).hexdigest() for x in (data,data.replace(b'\n',b'\r\n'))]:raise ValueError('Installed source-lock mismatch')
    wheel_files=0
    expected_wheels={p['name']:(p['version'],p['url'],p['sha256']) for p in lock['packages']}
    observed_wheels={w['name']:(w['version'],w['url'],w['sha256']) for w in installed['wheels']}
    if observed_wheels!=expected_wheels or len(installed['wheels'])!=len(expected_wheels):
        raise ValueError('Installed wheel closure differs from accepted lock')
    for w in installed['wheels']:
        p=root/'wheels'/w['filename']
        if file_record(p)!={k:w[k] for k in ('bytes','sha256')}:raise ValueError('Cached wheel changed')
        with zipfile.ZipFile(p) as z:
            for name in z.namelist():
                if name.endswith('/') or name.endswith('.dist-info/RECORD'):continue
                if '.data/' in name:continue # installed RECORD checked below; layout recorded as limitation
                dest=prefix/'Lib/site-packages'/name
                if hashlib.sha256(z.read(name)).hexdigest()!=file_record(dest)['sha256']:raise ValueError('Installed wheel member changed')
                wheel_files+=1
    installed_files=0
    for d in distributions:
        if Path(d.locate_file('')).resolve()!=prefix/'Lib/site-packages':raise ValueError('Foreign site package')
        for name,h,size in csv.reader(d.read_text('RECORD').splitlines()):
            if not h:continue
            alg,value=h.split('=',1);p=Path(d.locate_file(name)).resolve()
            if alg!='sha256' or not p.is_relative_to(prefix):raise ValueError('Installed RECORD path/hash')
            r=file_record(p)
            if base64.urlsafe_b64encode(bytes.fromhex(r['sha256'])).decode().rstrip('=')!=value or r['bytes']!=int(size):raise ValueError('Installed RECORD mismatch')
            installed_files+=1
    blas=threadpool_info()
    if any(v['num_threads']!=1 for v in blas):raise ValueError('Single-thread numerical libraries required')
    return dict(schema='bsfm.layer9-cpu-authentication.v1',runtime=runtime,executable=str(Path(sys.executable).resolve()),
        lock=file_record(lockpath),installed_receipt=file_record(root/'installed.json'),packages=actual,
        cpu=True,x64=True,blas=blas,installed_record_files=installed_files,wheel_member_files=wheel_files,
        limitation='Wheel .data entries use installed RECORD integrity; Windows CPU only')


def authenticate_files(files):
    for name,r in files.items():
        if set(r)!= {'path','bytes','sha256'} or file_record(r['path'])!={k:r[k] for k in ('bytes','sha256')}:raise ValueError('Input file changed: '+name)


def load_inputs(files,factor_ids,*,genesis_path=None,dataset_recipe=None,migration_geometry_audit=None):
    """Caller supplies expected file hashes from accepted registration; paths relocatable."""
    if dataset_recipe is not None:
        return _load_dataset_inputs(files,factor_ids,dataset_recipe,genesis_path,migration_geometry_audit)
    required={'registration','prepared','contract','mesh','gpinit','certificate','response_manifest','response_validation'}
    if set(files)!=required:raise ValueError('Exact runtime artifact closure required')
    authenticate_files(files)
    receipt=read_json(files['registration']['path']);c=read_json(files['contract']['path']);cert=read_json(files['certificate']['path'])
    if receipt['status']!='clean_commit_regeneration_passed_registration_accepted':raise ValueError('Unaccepted preparation registration')
    for role,rec in [('prepared',receipt['prepared_npz']),('contract',receipt['prepared_contract']),('mesh',receipt['upstream']['mesh']),('response_manifest',receipt['upstream']['response_manifest']),('response_validation',receipt['upstream']['validation'])]:
        if any(files[role][k]!=rec[k] for k in ('bytes','sha256')):raise ValueError('Preparation upstream join mismatch')
    if not any(all(files[a][k]==fit[b][k] for a,b in [('gpinit','output'),('certificate','certificate')] for k in ('bytes','sha256')) for fit in receipt['fits']):raise ValueError('Unregistered GPINIT pair')
    if (c['producer']['generating_commit']!=receipt['generating_commit'] or not c['producer']['worktree_clean']
        or c['source_sha256']!=files['prepared']['sha256'] or c['arrays']!=cert['input_identities']
        or cert['provenance']['contract_sha256']!=files['contract']['sha256']
        or cert['provenance']['input_sha256']!=files['prepared']['sha256'] or cert['factors']!=len(factor_ids)):
        raise ValueError('Canonical GPINIT/preparation binding mismatch')
    with np.load(files['prepared']['path'],allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
    identity=input_identity(d,section=c['section'],response_sha256=c['upstream']['response_h5']['sha256'],coordinate_system='october26_glial_min_max_span')
    if identity['arrays']!=c['arrays']:raise ValueError('Prepared array identities')
    inputs=ModelInput.authenticate(d,identity)
    with np.load(files['mesh']['path'],allow_pickle=False) as z:m={k:z[k].copy() for k in z.files}
    from bsfm.mesh.identities import logical
    if set(m)!=set(c['upstream']['mesh_arrays']) or any(logical(a)!=c['upstream']['mesh_arrays'][k]['sha256'] for k,a in m.items()):raise ValueError('Mesh payload identity')
    if not all(np.array_equal(m[a],d[b]) for a,b in [('source_rows','source_row_indices'),('cell_type','cell_id'),('slocs','slocs')]):raise ValueError('Full population mesh join')
    geometry_data=dict(terms=np.stack([m['fem_C']]+[m[f'fem_g{i}'] for i in range(1,7)]),vertices=m['mesh_vertices'],
        projector=m['A_full'],locations=m['slocs'],active_indices=m['active_indices_full'],source_rows=m['source_rows'],
        vertex_ids=np.array([f'vertex-{i}' for i in range(len(m['mesh_vertices']))]),cell_ids=d['cell_names'])
    expected_geometry=mesh_identity(geometry_data,section=c['section'],mesh_sha256=files['mesh']['sha256'])
    if genesis_path is None:
        geo=WarpGeometry.authenticate(geometry_data,expected_geometry)
    else:
        from .run_chart import geometry_from_genesis
        geo=geometry_from_genesis(geometry_data,expected_geometry,genesis_path,migration_audit=migration_geometry_audit)
    with np.load(files['gpinit']['path'],allow_pickle=False) as z:seeds={k:z[k].copy() for k in z.files}
    if {k:logical_hash(a) for k,a in seeds.items()}!=cert['output_logical_hashes']:raise ValueError('GPINIT output logical hashes')
    target=DirectWTarget(inputs,geo,load_rule(),factor_ids=tuple(factor_ids))
    binding=dict(files=files,preparation_commit=c['producer']['generating_commit'],target_identity=target.identity,
        spectral_identity=geo.spectral_identity,full_data=True,primary_holdout_scoring_eligible=False)
    return target,seeds['Lam_seed'],seeds['eta_seed'],binding


def _load_dataset_inputs(files,factor_ids,recipe,genesis_path,migration_geometry_audit=None):
    """Join existing prepared response, GPINIT certificate and warp NPZ contracts."""
    if (set(recipe)!={'schema','sample','coordinate_system','quadrature_order'}
        or recipe['schema']!='bsfm.dataset-run-inputs.v1'
        or recipe['coordinate_system']!='october26_glial_min_max_span'):
        raise ValueError('Explicit dataset recipe and accepted normalized coordinate chart required')
    if set(files)!={'prepared','contract','response_manifest','mesh','gpinit','certificate','rule'}:
        raise ValueError('Exact dataset runtime artifact closure required')
    authenticate_files(files)
    c=read_json(files['contract']['path']); response=read_json(files['response_manifest']['path'])
    cert=read_json(files['certificate']['path'])
    if (c['schema']!='bsfm.gpinit-input.v1' or c['response']!='final_centered_Y'
        or c['source_sha256']!=files['prepared']['sha256']
        or response['files']['training.npz']!=files['prepared']['sha256']
        or response['files']['gpinit-input.json']!=files['contract']['sha256']
        or response['sample']!=recipe['sample']):
        raise ValueError('Prepared response/contract/sample join mismatch')
    for key in ('dataset_manifest_sha256','selection_sha256','coordinate_transform','normalization','centering'):
        if c[key]!=response[key]:raise ValueError('Preparation metadata join mismatch: '+key)
    def bank(role):
        with np.load(files[role]['path'],allow_pickle=False) as z:
            if len(z.files)!=len(set(z.files)):raise ValueError('Duplicate NPZ members')
            return {k:z[k].copy() for k in z.files}
    d=bank('prepared')
    identity=input_identity(d,section=recipe['sample'],response_sha256=files['prepared']['sha256'],
                            coordinate_system=recipe['coordinate_system'])
    if identity['arrays']!=c['arrays']:raise ValueError('Prepared array identities')
    if (response['genes']!=d['gene_names'].tolist()
        or response['groups']!=d['cell_type_names'].tolist()):
        raise ValueError('Prepared gene/group order mismatch')
    inputs=ModelInput.authenticate(d,identity)
    if (cert['status']!='pass' or cert['schema']!='bsfm.gpinit-diagnostics.v1'
        or cert['input_identities']!=c['arrays'] or cert['factors']!=len(factor_ids)
        or cert['provenance']['input_sha256']!=files['prepared']['sha256']
        or cert['provenance']['contract_sha256']!=files['contract']['sha256']
        or cert['output_sha256']!=files['gpinit']['sha256']):
        raise ValueError('GPINIT certificate/preparation binding mismatch')
    seeds=bank('gpinit')
    if {k:logical_hash(a) for k,a in seeds.items()}!=cert['output_logical_hashes']:
        raise ValueError('GPINIT output logical hashes')
    g,n=d['Y'].shape; types=len(d['cell_type_names']); k=len(factor_ids)
    if cert['dimensions']!=dict(types=types,genes=g,cells=n):raise ValueError('GPINIT dimensions')
    array(seeds['Lam_seed'],'GPINIT loading',(types,g,k));array(seeds['eta_seed'],'GPINIT eta',(k,n))
    geometry_data=bank('mesh')
    expected=mesh_identity(geometry_data,section=recipe['sample'],mesh_sha256=files['mesh']['sha256'])
    # Reject mismatched population/order before spectral work or initialization.
    for left,right in [('slocs','locations'),('cell_names','cell_ids'),('source_row_indices','source_rows')]:
        if not np.array_equal(d[left],geometry_data[right]):raise ValueError('Prepared/mesh join mismatch: '+left)
    if genesis_path is None:
        geo=WarpGeometry.authenticate(geometry_data,expected)
    else:
        from .run_chart import geometry_from_genesis
        geo=geometry_from_genesis(geometry_data,expected,genesis_path,migration_audit=migration_geometry_audit)
    from .registry_rule import load_registry_rule
    rule=load_registry_rule(files['rule']['path'],expected_sha256=files['rule']['sha256'],order=recipe['quadrature_order'])
    target=DirectWTarget(inputs,geo,rule,factor_ids=tuple(factor_ids))
    binding=dict(files=files,dataset_recipe=recipe,response_manifest=response,
                 target_identity=target.identity,spectral_identity=geo.spectral_identity,
                 primary_holdout_scoring_eligible=False)
    return target,seeds['Lam_seed'],seeds['eta_seed'],binding


def canonical_controller(root,spec,files,*,gpu_runtime=None,dataset_recipe=None):
    """Authenticated prepared inputs with clean Git and explicit CPU/GPU environment.

    GPU deployment arguments come from a committed recipe; no CPU fallback.
    An explicit dataset_recipe selects the reusable prepared-artifact join;
    omission preserves the original registered S10 preparation contract.
    """
    from .run_controller import RunController,validate_spec
    from .run_storage import safe
    validate_spec(spec)
    def clean():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        if head!=spec['software']['git_commit'] or subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip():raise ValueError('Clean exact generating commit required')
    clean();env=authenticate_environment(gpu_runtime=gpu_runtime)
    if gpu_runtime is not None:
        from .run_gpu_environment import preflight_gpu_callback
        preflight_gpu_callback()
    genesis=safe(Path(root)/'segments'/spec['segment_id']/'genesis/endpoint.npz')
    target,loading,eta,binding=load_inputs(files,spec['factor_ids'],genesis_path=genesis if genesis.exists() else None,
                                        dataset_recipe=dataset_recipe)
    if (spec['software']['clean_tree'] is not True or spec['software']['environment_identity']!=digest(env)
        or spec['software']['environment_lock_sha256']!=env['lock']['sha256']):raise ValueError('Frozen environment declaration mismatch')
    if spec['software']['run_config_sha256']!=digest({k:v for k,v in spec.items() if k!='software'}):raise ValueError('Run specification hash mismatch')
    def authenticate():
        clean();authenticate_files(files)
        if authenticate_environment(gpu_runtime=gpu_runtime)!=env:raise ValueError('Environment changed')
        target._validate_identities()
    return RunController(root,target,loading,eta,spec,binding,authenticate=authenticate)
