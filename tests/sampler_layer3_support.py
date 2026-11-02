"""Bounded deterministic test systems and SHA-authenticated original target reference."""
import ast
import copy
import csv
import hashlib
import json
from pathlib import Path
import jax
import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np
from bsfm.sampler import contracts, warp
from bsfm.sampler.active import active_geometry
from bsfm.sampler.conjugate import compute_Yhat
from bsfm.sampler.shrinkage import compute_qgk
from bsfm.sampler.rule import load_rule
from bsfm.sampler.field_target import DirectWTarget,kernel_arguments
from sampler_layer2_support import synthetic
from sampler_provenance import selected_source_record

ROOT=Path(__file__).resolve().parents[1]


def system(seed=12):
    d=synthetic();d['cell_ids']=np.array(['cell-0','cell-1','cell-2'])
    geometry=warp.WarpGeometry.authenticate(d,warp.mesh_identity(d,section='synthetic',mesh_sha256='b'*64))
    rng=np.random.default_rng(seed);g,n,c,k=2,3,3,2
    raw=dict(Y=rng.normal(0,.3,(g,n)),slocs=d['locations'].copy(),cell_id=np.arange(c,dtype=np.int64),
             cell_names=d['cell_ids'].copy(),source_row_indices=d['source_rows'].copy(),
             gene_names=np.array(['gene-a','gene-b']),cell_type_names=np.array(['MIC','AST','OGC']))
    inputs=contracts.ModelInput.authenticate(raw,contracts.input_identity(raw,section='synthetic',response_sha256='a'*64,coordinate_system='october26_glial_min_max_span'))
    delta=np.array([1.1,.8])
    state=contracts.GaussianState(rng.normal(0,.4,(c,g,k)),rng.normal(0,.2,(k,n)),
        np.array([.8,.6]),np.array([.4,.6]),np.array([.5,.8]),np.full((g,k),1.1),delta,np.cumprod(delta),inputs.identity_json)
    target=DirectWTarget(inputs,geometry,load_rule(),factor_ids=('factor-a','factor-b'))
    z=rng.normal(0,.15,(len(d['active_indices']),2))
    pos=target.position('factor-b',log_alpha=np.log(.8),logit_zeta=-.3,log_ell=np.log(.7),log_r=np.log(.9),zW=z)
    return target,state,pos


def historical(source_root):
    namespace=dict(np=np,jax=jax,jnp=jnp,jsla=jsla,active_geometry=active_geometry,compute_qgk=compute_qgk)
    inventory=[]
    for name,functions in [
        ('fixed_splusu_dynamic_target.py',['_build_log_range_target','build_dynamic_fixed_target','sufficient_statistics','sample_single_eta']),
        ('direct_w_dynamic_target.py',['build_dynamic_fixed_target']),
        ('run_c3full_fixed_profile_nuts.py',['factor_context']),('rule_contract.py',['validate_rule'])]:
        p=Path(source_root)/name;b=p.read_bytes();r=selected_source_record(name)
        if len(b)!=int(r['bytes']) or hashlib.sha256(b).hexdigest()!=r['sha256']:raise ValueError('Source identity mismatch')
        tree=ast.parse(b.decode('utf-8-sig'));nodes=[copy.deepcopy(n) for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in functions]
        if name=='fixed_splusu_dynamic_target.py':
            # Only inactive containment import/construction is omitted. No stub
            # likelihood is injected; containment_enabled stays False throughout.
            for n in nodes:
                if n.name=='_build_log_range_target':n.body=[s for s in n.body if s.lineno not in (33,34)]
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p),'exec'),namespace)
        if name=='fixed_splusu_dynamic_target.py':namespace['build_base']=namespace['build_dynamic_fixed_target']
        inventory.append(dict(path=str(p),bytes=len(b),sha256=r['sha256'],functions={n.name:[n.lineno,n.end_lineno] for n in nodes}))
    return namespace,inventory


def evaluate(target,state,pos,reference=None):
    if reference is None:
        kernels=target._kernels
        u,ct,penalty,identity=target.context(state,factor_id=pos.factor_id,state_factor_ids=target.factor_ids)
        from bsfm.sampler.factor_statistics import sample_single_eta
        draw=sample_single_eta
    else:
        kwargs=kernel_arguments(target.inputs,target.geometry,target.rule)
        kwargs.update(live_ell_eta=False,live_warp_hypers=True,ell_u=1.,sigma_u=.3,containment_enabled=False)
        kernels=reference['build_dynamic_fixed_target'](**kwargs)
        yhat=compute_Yhat(state.loading,state.eta,state.validate(target.inputs,factors=len(target.factor_ids)))
        u,ct,penalty=reference['factor_context'](target.inputs.arrays['Y'],yhat,state.loading,state.eta,
            state.sigma2,state.phi,state.tau,np.full(len(target.factor_ids),.2),target.factor_ids.index(pos.factor_id),target.inputs.arrays['cell_id'])
        draw=reference['sample_single_eta']
    x=jnp.asarray(pos.values);ju,jct,jp=map(jnp.asarray,(u,ct,penalty))
    value,grad=kernels['value_grad'](x,ju,jct,jp)
    refvalue,refgrad=kernels['reference_value_grad'](x,ju,jct,jp)
    w,wa,phi=kernels['warp_features'](x)
    rng=np.random.default_rng(831);before=copy.deepcopy(rng.bit_generator.state)
    eta=draw(rng,features=np.asarray(phi),alpha=np.exp(pos.values[0]),zeta=float(jax.nn.sigmoid(x[1])),u=u,ct=ct)
    return dict(u=u.tolist(),ct=ct.tolist(),penalty=penalty,value=float(value),gradient=np.asarray(grad).tolist(),
                reference_value=float(refvalue),reference_gradient=np.asarray(refgrad).tolist(),
                W=np.asarray(w).tolist(),W_active=np.asarray(wa).tolist(),
                features_shape=list(phi.shape),features_sha256=contracts.logical_hash(np.asarray(phi)),
                eta=eta.tolist(),rng_before=before,rng_after=copy.deepcopy(rng.bit_generator.state))


def dense_target(target,state,pos,x):
    """Independent cell-space integration and raw-Q Cholesky, not feature Hessian/QR.

    Small-system reference only; directly expresses all priors in coupled chart.
    """
    u,ct,penalty,_=target.context(state,factor_id=pos.factor_id,state_factor_ids=target.factor_ids)
    g=target.geometry;t=jnp.asarray(g.arrays['terms']);idx=g.arrays['active_indices'];a=jnp.asarray(g.arrays['projector'][:,idx])
    kappa=jnp.sqrt(40.)/jnp.exp(x[2]);coeff=jnp.asarray(warp.BINOM)*warp.NORMCONST*kappa**(2-2*jnp.arange(7))
    precision=jnp.sum(coeff[:,None,None]*t,axis=0);full=jnp.linalg.inv(precision)
    root=jnp.linalg.cholesky(full[np.ix_(idx,idx)])
    wa=jnp.exp(x[2]+x[3]-.5*jnp.log(10.))*(root@x[4:].reshape(-1,2));w=a@wa
    phase=w@jnp.asarray(target.rule.arrays['omega']).T
    f=jnp.concatenate([jnp.cos(phase)*jnp.asarray(target.rule.arrays['sqrt_weights']),jnp.sin(phase)*jnp.asarray(target.rule.arrays['sqrt_weights'])],axis=1)
    alpha2=jnp.exp(2*x[0]);zeta=jax.nn.sigmoid(x[1]);cov=alpha2*(zeta*(f@f.T)+(1-zeta)*jnp.eye(len(u)))
    posterior_precision=jnp.linalg.inv(cov)+jnp.diag(jnp.asarray(u))
    likelihood=-.5*jnp.linalg.slogdet(cov)[1]-.5*jnp.linalg.slogdet(posterior_precision)[1]+.5*jnp.asarray(ct)@jnp.linalg.solve(posterior_precision,jnp.asarray(ct))
    prior=len(target.inputs.arrays['gene_names'])*len(target.inputs.arrays['cell_type_names'])*x[0]-.5*alpha2*penalty
    prior+=-.5*(x[0]-np.log(.7))**2/.7+2*jnp.log(zeta)+2*jnp.log1p(-zeta)-.5*jnp.sum(x[4:]**2)
    prior+=-.5*x[2]**2/.25-.5*x[3]**2/(.3**2)
    return likelihood+prior
