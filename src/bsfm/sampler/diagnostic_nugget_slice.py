"""Diagnostic-only nugget slice adapter for a bounded changing-Gibbs test."""
import time
import numpy as np
import jax
import jax.numpy as jnp
import blackjax
from blackjax.adaptation.window_adaptation import base, build_schedule
from .flat_control import FlatTransition
from .flat_method_audit import slice_one
from .split_kernels import make_logdensity, Info
from .variance_coordinates import to_original, to_variances, wrap_value_grad


class DiagnosticNuggetSlice(FlatTransition):
    """Not registered as a production policy; tuning's middle mass is unused."""
    def __init__(self,target,*,depth=8,width=1.,max_steps=16,max_shrink=256):
        super().__init__(target)
        self.controls=dict(width=width,max_steps=max_steps,max_shrink=max_shrink)
        self.original_ld=make_logdensity(target._kernels)
        ld=make_logdensity(dict(value_grad=wrap_value_grad(target._kernels["value_grad"])))
        self.value=jax.jit(lambda p,u,ct,penalty:ld(p,u,ct,penalty))
        indices=jnp.array([0,2])
        kernel=blackjax.nuts.build_kernel()
        @jax.jit
        def nuts(key,p,u,ct,penalty,step,mass):
            density=lambda x:ld(p.at[indices].set(x),u,ct,penalty)
            state=blackjax.nuts.init(p[indices],density)
            end,info=kernel(key,state,density,step,mass,max_num_doublings=depth)
            return p.at[indices].set(end.position),info
        self.nuts=nuts
        self.original_state=jax.jit(lambda p,u,ct,penalty:
            blackjax.nuts.init(to_original(p),lambda q:self.original_ld(q,u,ct,penalty)))

    def step(self,key,p,context,step,mass):
        sk,nk=jax.random.split(key)
        seed=int(np.asarray(jax.random.bits(sk,shape=(),dtype=jnp.uint32)))
        rng=np.random.default_rng(seed)
        n,cost=slice_one(lambda n:self.value(p.at[1].set(n),*context),
                        float(p[1]),rng,**self.controls)
        p=p.at[1].set(n)
        p,info=self.nuts(nk,p,*context,step,mass)
        jax.block_until_ready(p)
        return p,info,cost

    def fit_tuning(self,key,position,state,*,steps,maximum_seconds):
        args,_=self._inputs(key,position,state,self.target.factor_ids,None)
        p=to_variances(args[0]);context=args[1:]
        ai,au,af=base(True,.9);au=jax.jit(au);af=jax.jit(af)
        indices=jnp.array([0,2]);ads=ai(p[indices],.03)
        schedule=build_schedule(steps)
        started=time.monotonic();history=[]
        for stage in schedule:
            if time.monotonic()-started>maximum_seconds:
                raise TimeoutError("Slice warmup diagnostic budget")
            key,sub=jax.random.split(key)
            p,info,cost=self.step(sub,p,context,ads.step_size,ads.inverse_mass_matrix)
            ac=float(info.acceptance_rate)
            if not np.isfinite(ac):raise FloatingPointError("Nonfinite acceptance")
            ads=au(ads,stage,p[indices],min(1.,ac))
            history.append(dict(acceptance=ac,divergent=bool(info.is_divergent),
                                leapfrogs=int(info.num_integration_steps),**cost))
        step,mass=af(ads)
        packed=np.ones(3);packed[[0,2]]=np.asarray(mass)
        tuning=self.tuning(position.factor_id,step_size=float(step),hyper_step_size=1.,
                           inverse_mass_matrix=packed)
        return tuning,history

    def transition(self,key,position,state,tuning,*,state_factor_ids,prepared_context=None):
        args,audit=self._inputs(key,position,state,state_factor_ids,prepared_context)
        tuned=self._tuning(tuning,position.factor_id)
        p,ni,cost=self.step(key,to_variances(args[0]),args[1:],tuned["step_size"],
                            tuned["inverse_mass_matrix"][jnp.array([0,2])])
        original=self.original_state(p,*args[1:])
        ac=ni.acceptance_rate
        ac=jnp.where((ac>1)&(ac<=1+8*np.finfo(float).eps),1.,ac)
        momentum=jnp.zeros(3).at[jnp.array([0,2])].set(ni.momentum)
        info=Info(ac,ni.is_divergent,ni.num_integration_steps,ni.energy,momentum,
                  jnp.array([ac,0.]),jnp.array([ni.is_divergent,False]),
                  jnp.array([ni.num_integration_steps,0]),jnp.array([ni.energy,0.]),jnp.array(0.))
        audit.update(diagnostic_method="nugget_slice",slice_cost=cost,
                     trajectory_coordinates="log_spatial_variance,log_range; nugget fixed during NUTS")
        return self._result(original,info,position,audit)

