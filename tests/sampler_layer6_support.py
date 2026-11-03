"""Authenticated literal driver statements, separate from canonical orchestration."""
import ast
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import jax
import jax.numpy as jnp
import numpy as np

from bsfm.sampler.contracts import GaussianState, logical_hash
from bsfm.sampler.conjugate import compute_Yhat, sample_Lambda_twostage, sample_sigma2_twostage
from bsfm.sampler.shrinkage import compute_qgk, sample_phi, sample_delta_tau
from bsfm.sampler.px import refresh_alpha_gauge
from bsfm.sampler.factor_statistics import factor_context, sample_single_eta
from bsfm.sampler.joint_eta_kernels import sample_joint_eta_pcg
from bsfm.sampler.layer4 import STATE_ARRAYS
from bsfm.sampler.layer6 import GibbsSweep
from sampler_layer3_support import system
from sampler_layer4_support import positions
from sampler_layer5_support import tree_record
from sampler_provenance import selected_source_record

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'run_c3full_fixed_profile_nuts.py'
INNER_LINES = (1123,1127,1128,1131,1143,1145,1146)
FACTOR_LINES = (1181,1182,1183,1186,1188,1189,1193,1194,1198,1201,1202,1203,
                1204,1208,1212,1225,1263,1270)
TOP_LINES = (1121,1122,1150,1151,1156,1166,1170,1172,1179,1180)


def fixture_system():
    target, state, pos = system(12)
    ps = positions(target,state,pos)
    scale = .25*np.var(target.inputs.arrays['Y'],axis=1)
    layer = GibbsSweep(target,b_sigma2=scale)
    tuning = tuple(layer.split.tuning(fid) for fid in target.factor_ids)
    return target,state,ps,layer,tuning,scale


def independent_rng(eta_rng,gauge_rng,key):
    def convert(x):
        if isinstance(x,np.ndarray):return dict(dtype=x.dtype.str,shape=list(x.shape),values=x.tolist())
        if isinstance(x,np.generic):return x.item()
        raise TypeError(type(x))
    def digest(x):
        return hashlib.sha256(json.dumps(x,default=convert,sort_keys=True,
                allow_nan=False,separators=(',',':')).encode()).hexdigest()
    return dict(numpy_global_sha256=digest(np.random.get_state()),
        eta_generator=type(eta_rng.bit_generator).__name__,eta_rng_sha256=digest(eta_rng.bit_generator.state),
        gauge_generator=type(gauge_rng.bit_generator).__name__,gauge_rng_sha256=digest(gauge_rng.bit_generator.state),
        jax_impl=str(jax.random.key_impl(key)),jax_key_data=np.asarray(jax.random.key_data(key)).tolist())


def authenticated_literal(source_root):
    path=Path(source_root)/SOURCE; data=path.read_bytes(); record=selected_source_record(SOURCE)
    if len(data)!=int(record['bytes']) or hashlib.sha256(data).hexdigest()!=record['sha256']:
        raise ValueError('Chronology source identity mismatch')
    tree=ast.parse(data)
    # Select statements by authenticated source lines, not by reimplementing
    # the chronology in a second handwritten loop. No original main/imports.
    def at(line):
        return copy.deepcopy(next(n for n in ast.walk(tree)
            if isinstance(n,ast.stmt) and getattr(n,'lineno',None)==line))
    body=[]
    for line in TOP_LINES:
        n=at(line)
        if line==1122:n.body=[x for x in n.body if x.lineno in INNER_LINES]
        if line in (1151,1156):
            body.extend(n.body)  # selected ordinary shrinkage, never fixed precision
            continue
        if line==1180:
            n.body=[x for x in n.body if x.lineno in FACTOR_LINES]
            n.body+=ast.parse('reference_records.append((k, state, info, u.copy(), ct.copy(), penalty, np.asarray(step_key).copy()))').body
        body.append(n)
    constants=[at(line) for line in (41,42,48,49,50,51)]
    module=ast.fix_missing_locations(ast.Module(body=constants+body,type_ignores=[]))
    source_info=dict(path=str(path),bytes=len(data),sha256=record['sha256'],
        top_statement_lines=TOP_LINES,inner_statement_lines=INNER_LINES,factor_statement_lines=FACTOR_LINES,
        selected_AST_sha256=hashlib.sha256(ast.dump(module,include_attributes=False).encode()).hexdigest(),
        exclusions='captures, persistent diagnostics, containment/fidelity monitoring, fixed-loading-precision branch; no numerical/RNG update omitted')
    return compile(module,str(path),'exec'),source_info


def run_literal(code, target, state, ps, layer, tuning, scale, eta_rng, gauge_rng, key):
    ns=dict(np=np,jax=jax,jnp=jnp,**{n:np.array(getattr(state,n),copy=True) for n in STATE_ARRAYS})
    ns.update(y=target.inputs.arrays['Y'],v=np.ones_like(target.inputs.arrays['Y']),
        s=np.full(len(ps),.2),cell_id=target.inputs.arrays['cell_id'],
        cell_slices=state.validate(target.inputs,factors=len(ps)),cell_types=state.loading.shape[0],
        genes=state.loading.shape[1],factors=len(ps),b_sigma2=scale,
        positions=[jnp.asarray(p.values) for p in ps],targets=[target._kernels]*len(ps),
        transitions=[lambda key,p,u,ct,penalty,t=t:layer.split._runner['transition'](
            key,p,u,ct,penalty,dict(step_size=jnp.asarray(t.step_size),hyper_step_size=jnp.asarray(t.hyper_step_size),inverse_mass_matrix=jnp.asarray(t.inverse_mass_matrix))) for t in tuning],
        args=SimpleNamespace(pcg_tolerance=1e-10,pcg_max_iterations=80,split_E=True,
                             live_ell_eta=False,live_warp_hypers=True,direct_w=True),
        rng=eta_rng,gauge_rng=gauge_rng,master_key=key,sweep=1,
        ell_eta_reference=.14,ell_u_position_index=2,sigma_u_position_index=3,
        ell_eta_state=np.zeros(len(ps)),ell_u_state=np.zeros(len(ps)),sigma_u_state=np.zeros(len(ps)),
        reference_records=[],sample_Lambda_twostage=sample_Lambda_twostage,
        sample_joint_eta_pcg=sample_joint_eta_pcg,compute_Yhat=compute_Yhat,
        sample_sigma2_twostage=sample_sigma2_twostage,compute_qgk=compute_qgk,
        sample_phi=sample_phi,sample_delta_tau=sample_delta_tau,refresh_alpha_gauge=refresh_alpha_gauge,
        factor_context=factor_context,sample_single_eta=sample_single_eta)
    def finite(*values):
        if not all(np.isfinite(x).all() for x in values):raise RuntimeError('Nonfinite source endpoint')
    ns['require_finite']=finite
    exec(code,ns)
    return ns


def record_result(result):
    return dict(state={n:getattr(result.state,n).tolist() for n in STATE_ARRAYS},
        positions=[p.values.tolist() for p in result.positions],order=list(result.factor_order),
        yhat=result.fitted_Y.tolist(),pcg=[asdict(x) for x in result.pcg_diagnostics],px=result.px_audit,
        factor_outputs=[dict(index=x['factor_index'],leaves=tree_record((x['transition'].nuts_state,x['transition'].info)),
            u_sha256=x['transition'].audit['context']['u_sha256'],ct_sha256=x['transition'].audit['context']['ct_sha256'],
            penalty=x['transition'].audit['context']['penalty'],key=x['transition'].audit['key_data']) for x in result.factor_diagnostics],
        warp=list(result.warp_summaries),rng_before=result.audit['rng_before'],rng_after=result.audit['rng_after'])


def run_case(reference=None):
    target,state,ps,layer,tuning,scale=fixture_system()
    saved=np.random.get_state()
    try:
        np.random.seed(491);eta_rng=np.random.default_rng(193);gauge_rng=np.random.default_rng(307)
        key=jax.random.PRNGKey(419);before=independent_rng(eta_rng,gauge_rng,key)
        if reference is None:
            result=layer.sweep(state,ps,tuning,eta_rng=eta_rng,gauge_rng=gauge_rng,master_key=key,
                              state_factor_ids=target.factor_ids,label='sweep_0001')
            out=record_result(result)
            assert out['rng_before']==before and out['rng_after']==independent_rng(eta_rng,gauge_rng,result.master_key)
            return out
        ns=run_literal(reference,target,state,ps,layer,tuning,scale,eta_rng,gauge_rng,key)
        return dict(state={n:ns[n].tolist() for n in STATE_ARRAYS},positions=[np.asarray(p).tolist() for p in ns['positions']],
            order=ns['order'].tolist(),yhat=ns['yhat'].tolist(),pcg=[asdict(x) for x in ns['sweep_pcg']],px=ns['gauge'],
            factor_outputs=[dict(index=k,leaves=tree_record((s,info)),u_sha256=logical_hash(u),ct_sha256=logical_hash(ct),penalty=penalty,key=key.tolist())
                            for k,s,info,u,ct,penalty,key in ns['reference_records']],
            warp=[dict(factor_id=fid,ell_eta=ns['ell_eta_state'][i],ell_W=ns['ell_u_state'][i],sigma_W=ns['sigma_u_state'][i]) for i,fid in enumerate(target.factor_ids)],
            rng_before=before,rng_after=independent_rng(eta_rng,gauge_rng,ns['master_key']))
    finally:np.random.set_state(saved)
