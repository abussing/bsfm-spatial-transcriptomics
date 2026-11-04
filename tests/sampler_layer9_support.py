"""Synthetic inputs and SHA-authenticated bounded initialization reference."""
import ast
import copy
import hashlib
import os
import sys
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace
import jax
import jax.numpy as jnp
import numpy as np
from scipy.linalg import solve_triangular
from sampler_layer6_support import fixture_system
from sampler_provenance import selected_source_record
from bsfm.sampler.conjugate import compute_Yhat,sample_sigma2_twostage
from bsfm.sampler.px import refresh_alpha_gauge
from bsfm.sampler.active import active_geometry
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.run_controller import RunController

ROOT=Path(__file__).resolve().parents[1]
BASE='9c584353e74043e323ca327ff1764f9d094980d5'
SYSTEM=lru_cache(maxsize=1)(fixture_system)


def controller(path,*,every=2,settling=0,final=2):
    target,state,_,layer,_,_=SYSTEM()
    binding=dict(kind='synthetic_layer9_test',target=target.identity)
    spec=dict(schema='bsfm.local-run.v1',run_id='mechanical',segment_id='segment',chain_id='chain',
        factor_ids=list(target.factor_ids),seed=491,warmup_steps=20,settling_sweeps=settling,
        production_sweeps=final-settling,final_sweep=final,save_every=2,checkpoint_every=every,
        mode='exact_resume',input_sha256=digest(binding),software=dict(git_commit=BASE,clean_tree=False,
            run_config_sha256=digest(dict(scope='synthetic',every=every,settling=settling,final=final)),
            environment_lock_sha256=hashlib.sha256((ROOT/'environment/sampler-layer5/source-lock.json').read_bytes()).hexdigest(),
            environment_identity='layer9-'+sys.platform+'-CPU:synthetic-review'))
    result=RunController(path,target,state.loading,state.eta,spec,binding,authenticate=target._validate_identities)
    result.layer=layer
    return result


def literal_initialization(target,loading,eta,seed):
    path=Path(os.environ.get('BSFM_HISTORICAL_DRIVER',r'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler\run_c3full_fixed_profile_nuts.py'))
    raw=path.read_bytes();r=selected_source_record(path.name)
    assert len(raw)==int(r['bytes']) and hashlib.sha256(raw).hexdigest()==r['sha256']
    tree=ast.parse(raw);lines=(466,467,477,478,479,480,482,483,484,485,489,493,494,495,496,510,511,514,517,518,662,663)
    body=[]
    for line in lines:
        node=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.stmt) and n.lineno==line))
        if line==518:
            # Imports only: use authenticated accepted dependency already supplied;
            # no historical sys.path or top-level driver execution.
            node.body=[s for s in node.body if s.lineno!=533]
            for n in node.body:
                if isinstance(n,ast.If) and n.lineno==525:n.body=[s for s in n.body if not isinstance(s,(ast.Import,ast.ImportFrom))]
        body.append(node)
    module=ast.fix_missing_locations(ast.Module(body=body,type_ignores=[]))
    c,g,k=loading.shape;y=target.inputs.arrays['Y'];codes=target.inputs.arrays['cell_id']
    cuts=np.r_[0,np.cumsum(np.bincount(codes))]
    ns=dict(np=np,jax=jax,jnp=jnp,args=SimpleNamespace(seed=seed,live_ell_eta=False,live_warp_hypers=True,direct_w=True,sigma_u_prior_center=.31622776601683794),
        lambda_gpinit=loading,eta_gpinit=eta,genes=g,factors=k,y=y,FIXED_SHARING_S=.2,
        cell_slices=tuple(slice(int(a),int(b)) for a,b in zip(cuts[:-1],cuts[1:])),
        compute_Yhat=compute_Yhat,sample_sigma2_twostage=sample_sigma2_twostage,refresh_alpha_gauge=refresh_alpha_gauge,
        active=target.geometry.arrays['active_indices'],spectral=target.geometry.spectral,slocs=target.inputs.arrays['slocs'],
        data=dict(mesh_vertices=target.geometry.arrays['vertices'],A_active=target.geometry.arrays['projector'][:,target.geometry.arrays['active_indices']]),
        active_geometry=active_geometry,solve_triangular=solve_triangular,mu_log_ell_u=0.,mu_log_sigma_u=-.5*np.log(10.))
    exec(compile(module,str(path),'exec'),ns)
    return ns,dict(path=str(path),bytes=len(raw),sha256=r['sha256'],statement_lines=list(lines),AST_sha256=hashlib.sha256(ast.dump(module,include_attributes=False).encode()).hexdigest())
