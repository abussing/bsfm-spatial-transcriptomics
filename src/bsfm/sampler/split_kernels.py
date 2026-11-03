"""E update for full collapsed factor p=(log alpha, logit zeta,x,b,zW).

Field block includes alpha,zeta and zW. Hyper block holds PHYSICAL W fixed.
Eta is absent from both conditionals and must be refreshed by the Gibbs driver
immediately after this composite transition. No intermediate eta refresh.
"""
from collections import namedtuple
import numpy as np
import jax
import jax.numpy as jnp
import blackjax
from blackjax.adaptation.window_adaptation import base, build_schedule

Info = namedtuple('SplitInfo', 'acceptance_rate is_divergent num_integration_steps energy momentum block_acceptance block_divergent block_leapfrogs block_energy hyper_W_relative_error')
History = namedtuple('History','state info adaptation_state')
AdaptView = namedtuple('AdaptView','step_size inverse_mass_matrix')


def build_split(ld, maps, dimension, target=.9, depth=10):
    field = jnp.concatenate((jnp.arange(2),jnp.arange(4,dimension)))
    hyper = jnp.array([2,3])
    indices = (field,hyper)
    kernel = blackjax.nuts.build_kernel()

    def pack_mass(ads):
        return jnp.ones(dimension).at[field].set(ads[0].inverse_mass_matrix).at[hyper].set(ads[1].inverse_mass_matrix)

    def one(key,p,u,ct,penalty,field_step,hyper_step,mass):
        kf,kh = jax.random.split(key)
        full = lambda q:ld(q,u,ct,penalty)
        density = lambda v:full(p.at[field].set(v))
        s = blackjax.nuts.init(p[field],density)
        sf,fi = kernel(kf,s,density,field_step,mass[field],max_num_doublings=depth)
        pf = p.at[field].set(sf.position)
        W = maps['physical'](pf[2:4],pf[4:].reshape(-1,2))
        hd = lambda xb:maps['logdensity'](xb,W)
        sh = blackjax.nuts.init(pf[2:4],hd)
        sh,hi = kernel(kh,sh,hd,hyper_step,mass[hyper],max_num_doublings=depth)
        pn = pf.at[2:4].set(sh.position)
        pn = pn.at[4:].set(maps['whiten'](sh.position,W).reshape(-1))
        Wn = maps['physical'](pn[2:4],pn[4:].reshape(-1,2))
        invariant = jnp.linalg.norm(Wn-W)/jnp.maximum(jnp.linalg.norm(W),1e-100)
        ac = jnp.array([fi.acceptance_rate,hi.acceptance_rate])
        dv = jnp.array([fi.is_divergent,hi.is_divergent])
        lf = jnp.array([fi.num_integration_steps,hi.num_integration_steps])
        # Legacy energy diagnostic explicitly describes the FIELD block only.
        # Its momentum is padded with zeros in hyper positions, never combined
        # with the hyper block's different-chart Hamiltonian.
        info = Info(ac.mean(),dv.any(),lf.sum(),fi.energy,
                    jnp.zeros(dimension).at[field].set(fi.momentum),ac,dv,lf,
                    jnp.array([fi.energy,hi.energy]),invariant)
        return blackjax.nuts.init(pn,full),info,pf

    def transition(key,p,u,ct,penalty,tuned):
        state,info,_ = one(key,p,u,ct,penalty,tuned['step_size'],tuned['hyper_step_size'],tuned['inverse_mass_matrix'])
        return state,info

    def adapt(key,p,u,ct,penalty,steps):
        if steps<20:raise ValueError('Split window adaptation requires >=20 transitions')
        ai,au,af = base(True,target)
        ads = tuple(ai(p[idx],.01) for idx in indices)
        schedule = build_schedule(steps)
        keys = jax.random.split(key,steps)
        def step(carry,item):
            p,ads=carry
            key,stage=item
            state,info,pf=one(key,p,u,ct,penalty,ads[0].step_size,ads[1].step_size,pack_mass(ads))
            new = (au(ads[0],stage,pf[field],info.block_acceptance[0]),
                   au(ads[1],stage,state.position[hyper],info.block_acceptance[1]))
            view=AdaptView(new[0].step_size,pack_mass(new))
            return (state.position,new),History(state,info,view)
        scan=jax.jit(lambda carry,items:jax.lax.scan(step,carry,items))
        histories=[]
        for start in range(0,steps,20):
            (p,ads),hist=scan((p,ads),(keys[start:start+20],schedule[start:start+20]))
            jax.block_until_ready(p)
            histories.append(hist)
            print('SPLIT WARMUP',min(start+20,steps),'/',steps,
                  'acceptance',np.round(np.asarray(hist.info.block_acceptance).mean(axis=0),3).tolist(),
                  'divergences',np.asarray(hist.info.block_divergent).sum(axis=0).tolist(),flush=True)
        hist=jax.tree.map(lambda *xs:jnp.concatenate(xs),*histories)
        f,h = af(ads[0]),af(ads[1])
        mass=jnp.ones(dimension).at[field].set(f[1]).at[hyper].set(h[1])
        tuned=dict(step_size=f[0],hyper_step_size=h[0],inverse_mass_matrix=mass)
        assert float(jnp.max(hist.info.hyper_W_relative_error))<2e-8
        state=blackjax.nuts.init(p,lambda q:ld(q,u,ct,penalty))
        return (state,tuned),hist
    return dict(transition=jax.jit(transition),adapt=adapt)


# Selected driver analytic-gradient bridge; provenance in LAYER5_SOURCE_MAP.csv.
def make_logdensity(target):
    @jax.custom_vjp
    def logdensity(position, u, ct, penalty):
        return target["value_grad"](position, u, ct, penalty)[0]

    # Custom VJP cotangents for u/ct must match their shapes; close them into
    # the residual alongside the analytic position gradient.
    def fwd(position, u, ct, penalty):
        value, gradient = target["value_grad"](position, u, ct, penalty)
        return value, (gradient, u, ct, penalty)

    def bwd(residual, cotangent):
        gradient, u, ct, penalty = residual
        return (
            cotangent * gradient, jnp.zeros_like(u), jnp.zeros_like(ct),
            jnp.zeros_like(penalty),
        )

    logdensity.defvjp(fwd, bwd)
    return logdensity
