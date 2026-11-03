"""Authenticated NPZ-only runtime entry. No h5py, R, sklearn or helper interpreter."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import os
from pathlib import Path
import site
import subprocess
import sys
import zipfile
import numpy as np
import jax
from threadpoolctl import threadpool_info
from .contracts import ModelInput, input_identity, logical_hash
from .warp import WarpGeometry, mesh_identity
from .field_target import DirectWTarget
from .rule import load_rule
from .checkpoint_contract import digest
from .run_storage import file_record, read_json

REPO=Path(__file__).resolve().parents[3]


def authenticate_environment():
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
    for r in lock['runtime']:
        if file_record(r['path'])!={k:r[k] for k in ('bytes','sha256')}:raise ValueError('Runtime changed')
    installed=read_json(root/'installed.json')
    for filename,field in [('source-lock.json','lock_sha256'),('requirements.lock.txt','requirements_sha256')]:
        data=(lockpath.parent/filename).read_bytes()
        if installed[field] not in [hashlib.sha256(x).hexdigest() for x in (data,data.replace(b'\n',b'\r\n'))]:raise ValueError('Installed source-lock mismatch')
    wheel_files=0
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
    return dict(schema='bsfm.layer9-cpu-authentication.v1',runtime=lock['runtime'],executable=str(Path(sys.executable).resolve()),
        lock=file_record(lockpath),installed_receipt=file_record(root/'installed.json'),packages=actual,
        cpu=True,x64=True,blas=blas,installed_record_files=installed_files,wheel_member_files=wheel_files,
        limitation='Wheel .data entries use installed RECORD integrity; Windows CPU only')


def authenticate_files(files):
    for name,r in files.items():
        if set(r)!= {'path','bytes','sha256'} or file_record(r['path'])!={k:r[k] for k in ('bytes','sha256')}:raise ValueError('Input file changed: '+name)


def load_inputs(files,factor_ids):
    """Caller supplies expected file hashes from accepted registration; paths relocatable."""
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
    geo=WarpGeometry.authenticate(geometry_data,mesh_identity(geometry_data,section=c['section'],mesh_sha256=files['mesh']['sha256']))
    with np.load(files['gpinit']['path'],allow_pickle=False) as z:seeds={k:z[k].copy() for k in z.files}
    if {k:logical_hash(a) for k,a in seeds.items()}!=cert['output_logical_hashes']:raise ValueError('GPINIT output logical hashes')
    target=DirectWTarget(inputs,geo,load_rule(),factor_ids=tuple(factor_ids))
    binding=dict(files=files,preparation_commit=c['producer']['generating_commit'],target_identity=target.identity,
        spectral_identity=geo.spectral_identity,full_data=True,primary_holdout_scoring_eligible=False)
    return target,seeds['Lam_seed'],seeds['eta_seed'],binding


def canonical_controller(root,spec,files):
    """Only real-artifact entry: clean committed tree and current locked environment."""
    from .run_controller import RunController
    def clean():
        head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        if head!=spec['software']['git_commit'] or subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip():raise ValueError('Clean exact generating commit required')
    clean();env=authenticate_environment();target,loading,eta,binding=load_inputs(files,spec['factor_ids'])
    if (spec['software']['clean_tree'] is not True or spec['software']['environment_identity']!=digest(env)
        or spec['software']['environment_lock_sha256']!=env['lock']['sha256']):raise ValueError('Frozen environment declaration mismatch')
    if spec['software']['run_config_sha256']!=digest({k:v for k,v in spec.items() if k!='software'}):raise ValueError('Run specification hash mismatch')
    def authenticate():
        clean();authenticate_files(files)
        if authenticate_environment()!=env:raise ValueError('Environment changed')
        target._validate_identities()
    return RunController(root,target,loading,eta,spec,binding,authenticate=authenticate)
