"""Selected F/C initialization and sequential retained warmup; no run defaults.

Driver eb452c4c:466-538,662-665,697-734,906-949. Numerical kernels
are accepted Layers 1-5. Initial sigma is the historical literal, not exp(log).
"""
import copy
from dataclasses import dataclass
import jax
import jax.numpy as jnp
import numpy as np
from scipy.linalg import solve_triangular
from .contracts import GaussianState, array, logical_hash
from .conjugate import compute_Yhat, sample_sigma2_twostage
from .px import refresh_alpha_gauge
from .field_target import FieldPosition
from .layer4 import state_hashes
from .layer5 import SplitTransition, MIN_ADAPTATION_STEPS
from .checkpoint_rng import stream_audit
from .retained_diagnostics import encode


@dataclass
class Endpoint:
    state: object
    positions: tuple
    tuning: tuple
    eta_rng: object
    gauge_rng: object
    master_key: object
    numpy_global_state: tuple
    b_sigma2: np.ndarray
    evidence: dict


def initialize(target, loading, eta, *, seed):
    """Exactly one initial sigma2 draw and PX; caller explicitly supplies seed."""
    target._validate_identities()
    if type(seed) is not int or not 0 <= seed <= 2**32-3004:
        raise ValueError('Explicit seed and offsets must fit uint32')
    k=len(target.factor_ids); y=target.inputs.arrays['Y']; g,n=y.shape
    c=len(target.inputs.arrays['cell_type_names'])
    array(loading,'GPINIT loading',(c,g,k));array(eta,'GPINIT eta',(k,n))
    # Validate fixed noise scale before advancing any stream.
    b=.25*np.var(y,axis=1);array(b,'initial noise scale',(g,),positive=True)
    np.random.seed(seed);eta_rng=np.random.default_rng(seed)
    alpha=np.maximum(eta.std(axis=1),1e-3)
    state=GaussianState(loading.copy(),eta.copy(),alpha.copy(),np.full(k,.5),
        np.ones(g),np.ones((g,k)),np.ones(k),np.cumprod(np.ones(k)),target.inputs.identity_json)
    slices=state.validate(target.inputs,factors=k)
    signal=compute_Yhat(state.loading,state.eta,slices)
    state.sigma2=sample_sigma2_twostage(y,signal,np.ones_like(y),2.,b)
    before=state_hashes(state)
    gauge=np.random.default_rng(seed+3003)
    state.loading,state.eta,state.alpha,px=refresh_alpha_gauge(
        state.loading,state.eta,state.alpha,gauge,np.full(k,.2),'gpinit_initial')
    positions=[]; sigma=.31622776601683794
    for i,fid in enumerate(target.factor_ids):
        chol=np.asarray(target.geometry.geometry(0.)[0])
        center=np.mean(target.inputs.arrays['slocs'],axis=0)
        idx=target.geometry.arrays['active_indices']
        identity=target.geometry.arrays['vertices'][idx]-center
        latent=solve_triangular(chol,identity/sigma,lower=True)
        projected=target.geometry.arrays['projector'][:,idx]@(sigma*chol@latent)
        np.testing.assert_allclose(projected,target.inputs.arrays['slocs']-center,atol=1e-9,rtol=1e-9)
        values=np.asarray(jnp.concatenate((jnp.asarray([np.log(state.alpha[i]),np.log(state.zeta[i]/(1-state.zeta[i])),0.,0.],jnp.float64),jnp.asarray(latent.ravel(),jnp.float64)))).copy()
        values.flags.writeable=False;positions.append(FieldPosition(values,fid,target.identity))
    keys=jax.random.split(jax.random.PRNGKey(seed+1),k+1)
    evidence=dict(schema='bsfm.initialization.v1',seed=seed,initial_sigma_literal=sigma,
        before_PX=before,after_PX=state_hashes(state),px=encode(px),
        initial_signal_error=float(np.max(abs(compute_Yhat(state.loading,state.eta,slices)-signal))),
        master_key=np.asarray(keys[0]).tolist(),warm_keys=[np.asarray(x).tolist() for x in keys[1:]],
        initial_positions=[logical_hash(p.values) for p in positions],
        fidelity_status='not_evaluated_by_layers_1_to_8')
    return Endpoint(state,tuple(positions),(),eta_rng,gauge,keys[0],np.random.get_state(),b,evidence),tuple(keys[1:])


def adapt(target, endpoint, warm_keys, *, steps, split=None):
    """Natural factor order; keep each endpoint and draw one eta before next."""
    if type(steps) is not int or steps<MIN_ADAPTATION_STEPS:raise ValueError('Warmup requires >=20 steps')
    if len(warm_keys)!=len(target.factor_ids):raise ValueError('Missing ordered warmup keys')
    split=SplitTransition(target) if split is None else split
    if split.target is not target:raise ValueError('Foreign adaptation target')
    work=copy.deepcopy(endpoint.state);ps=list(endpoint.positions);tuning=[];histories=[]
    np.random.set_state(endpoint.numpy_global_state)
    before=stream_audit(endpoint.eta_rng,endpoint.gauge_rng,endpoint.master_key,np.random.get_state())
    for i,fid in enumerate(target.factor_ids):
        state_before=state_hashes(work)
        result=split.adapt(warm_keys[i],ps[i],work,state_factor_ids=target.factor_ids,steps=steps)
        ps[i]=result.endpoint.position;tuning.append(result.tuning)
        work.alpha[i]=float(np.exp(np.asarray(ps[i].values[0])))
        work.zeta[i]=float(jax.nn.sigmoid(jnp.asarray(ps[i].values[1])))
        work.eta[i],eta_audit=target.draw_eta(ps[i],work,endpoint.eta_rng,state_factor_ids=target.factor_ids)
        for key in ('u_sha256','ct_sha256'):
            if eta_audit[key]!=result.endpoint.audit['context'][key]:raise RuntimeError('Warmup eta conditional changed')
        histories.append(dict(factor_id=fid,state_before=state_before,state_after=state_hashes(work),
            key=np.asarray(warm_keys[i]).tolist(),history=encode(result.history),
            endpoint_audit=result.endpoint.audit,eta_audit=eta_audit))
    after=stream_audit(endpoint.eta_rng,endpoint.gauge_rng,endpoint.master_key,np.random.get_state())
    for key in ('numpy_global_sha256','gauge_rng_sha256','jax_key_data'):
        if before[key]!=after[key]:raise RuntimeError('Warmup advanced forbidden RNG stream')
    work.validate(target.inputs,factors=len(target.factor_ids))
    evidence=dict(initialization=endpoint.evidence,adaptation_steps=steps,target_acceptance=.9,
        factors=histories,rng_before=before,rng_after=after)
    return Endpoint(work,tuple(ps),tuple(tuning),endpoint.eta_rng,endpoint.gauge_rng,
                    endpoint.master_key,np.random.get_state(),endpoint.b_sigma2.copy(),evidence)
