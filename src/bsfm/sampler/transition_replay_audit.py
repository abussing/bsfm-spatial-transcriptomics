"""Replay one published transition, then diagnose its fixed field conditional.

Private output only. No adaptation, retries, continuation, or scientific draws.
"""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
import jax
import jax.numpy as jnp
from . import run_inputs
from .run import check_repository
from .run_checkpoint_fork import source_endpoint
from .checkpoint_contract import digest
from .layer6 import GibbsSweep
from .layer4 import JointEtaConditional
from .flat_control import FlatTarget,FlatTransition


def energy_path(value_grad,q,p,mass,step,steps):
    """Deterministic Euclidean leapfrog diagnostic; not a sampling kernel."""
    v,g=value_grad(q);h0=-v+.5*jnp.dot(p,mass*p)
    def one(carry,_):
        q,p,g=carry
        p=p+.5*step*g;q=q+step*mass*p
        v,g=value_grad(q);p=p+.5*step*g
        return (q,p,g),-v+.5*jnp.dot(p,mass*p)-h0
    (_,_,_),errors=jax.lax.scan(one,(q,p,g),None,length=steps)
    return errors


def run(path,commit):
    check_repository(path,commit);plan=json.loads(Path(path).read_text())
    if plan['source_commit']!=commit:raise ValueError('Wrong diagnostic commit')
    root=Path(plan['output']).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()):raise ValueError('External output required')
    root.mkdir(parents=True,exist_ok=True)
    class Captured(Exception):pass
    for case in plan['cases']:
        run_inputs.authenticate_files(dict(recipe=case['recipe'],expected=case['expected'],**case['source']))
        recipe=json.loads(Path(case['recipe']['path']).read_text())
        if 'transition_policy' in recipe:
            raise ValueError('This energy-replay audit expects original-coordinate tuning')
        env=run_inputs.authenticate_environment(gpu_runtime=recipe['gpu_runtime'])
        target,loading,eta,_=run_inputs.load_inputs(recipe['files'],recipe['factor_ids'],genesis_path=case['source']['genesis']['path'],dataset_recipe=recipe['dataset_recipe'])
        if recipe['model']=='flat':target=FlatTarget(target.inputs,target.geometry,target.rule,factor_ids=target.factor_ids,range_prior=recipe['flat_range_prior'])
        dest=root/case['name'];dest.mkdir(exist_ok=True)
        if (dest/'report.json').exists():raise ValueError('Refuse to overwrite replay')
        endpoint,binding=source_endpoint(case['source'],target,loading,eta,seed=recipe['seed'],environment_identity=digest(env),output=dest)
        layer=GibbsSweep(target,b_sigma2=endpoint.b_sigma2)
        layer.joint_eta=JointEtaConditional(target,maximum_iterations=recipe.get('pcg_maximum_iterations',320))
        if recipe['model']=='flat':layer.split=FlatTransition(target)
        idx=case['factor']-1
        fields=np.arange(target.position_dimension) if recipe['model']=='flat' else np.r_[0,1,np.arange(4,target.position_dimension)]
        expected=next(r for r in json.loads(Path(case['expected']['path']).read_text()) if r['sweep']==case['sweep'])
        expected=next(f for f in expected['factors'] if f['index']==idx)
        original=layer.split.transition
        def capture(key,position,state,tuning,**kwargs):
            if position.factor_id!=target.factor_ids[idx]:return original(key,position,state,tuning,**kwargs)
            c=kwargs['prepared_context'];q=jnp.asarray(position.values);mass=jnp.asarray(tuning.inverse_mass_matrix[fields]);h=float(tuning.step_size)
            result=original(key,position,state,tuning,**kwargs)
            actual=dict(acceptance=np.asarray(result.info.block_acceptance).tolist(),divergent=np.asarray(result.info.block_divergent).tolist(),leapfrogs=np.asarray(result.info.block_leapfrogs).tolist())
            np.testing.assert_allclose(actual['acceptance'],expected['acceptance'],rtol=1e-9,atol=1e-11)
            np.testing.assert_array_equal(actual['divergent'],expected['divergent'])
            np.testing.assert_array_equal(actual['leapfrogs'],expected['leapfrogs'])
            np.savez_compressed(dest/'conditional.npz',position=q,u=c.u,ct=c.ct,penalty=c.penalty,inverse_mass=tuning.inverse_mass_matrix,step=h,key=np.asarray(key),momentum=np.asarray(result.info.momentum))
            def vg(x):
                v,g=target._kernels['value_grad'](q.at[fields].set(x),jnp.asarray(c.u),jnp.asarray(c.ct),jnp.asarray(c.penalty))
                return v,g[fields]
            vg=jax.jit(vg);x=q[fields];value,gradient=vg(x)
            report=dict(case=case,source=binding,source_commit=commit,exact_diagnostic_replay=True,expected=expected,actual=actual,field_step=h,parameters=np.asarray(q[:4]).tolist(),alpha2_u_range=(np.exp(2*float(q[0]))*np.array([min(c.u),max(c.u)])).tolist(),gradient_checks=[],scalar_hessians=[],energy_tests=[])
            directions=np.eye(len(fields))[:2]
            for di in directions:
                exact=float(gradient@di);tests=[]
                for eps in [1e-3,3e-4,1e-4]:
                    vp,gp=vg(x+eps*di);vm,gm=vg(x-eps*di)
                    tests.append(dict(epsilon=eps,scaled_error=float(abs((vp-vm)/(2*eps)-exact)/max(1.,abs(exact)))))
                report['gradient_checks'].append(tests)
            for eps in [3e-4,1e-4]:
                H=np.column_stack([-(np.asarray(vg(x+eps*di)[1][:2])-np.asarray(vg(x-eps*di)[1][:2]))/(2*eps) for di in directions]);H=(H+H.T)/2
                D=np.sqrt(np.asarray(mass[:2]));ev=np.linalg.eigvalsh(D[:,None]*H*D[None,:])
                report['scalar_hessians'].append(dict(epsilon=eps,hessian=H.tolist(),mass_scaled_eigenvalues=ev.tolist(),local_step_number=float(h*np.sqrt(max(0.,ev[-1])))))
            # Same initial momentum and total integration time; changes resolution only.
            momentum=jnp.asarray(result.info.momentum)[fields]
            integrate=jax.jit(lambda step,steps:energy_path(vg,x,momentum,mass,step,steps),static_argnums=1)
            for sign in [-1,1]:
                for divisor in [1,2,4,8]:
                    errors=np.asarray(integrate(sign*h/divisor,8*divisor))
                    finite=bool(np.isfinite(errors).all())
                    report['energy_tests'].append(dict(direction=sign,step_divisor=divisor,steps=8*divisor,finite=finite,final_error=float(errors[-1]) if finite else None,max_abs_error=float(np.max(abs(errors))) if finite else None))
                    print('ENERGY',case['name'],report['energy_tests'][-1],flush=True)
            (dest/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
            print('REPLAY_COMPLETE',case['name'],flush=True)
            raise Captured()
        layer.split.transition=capture;np.random.set_state(endpoint.numpy_global_state)
        try:layer.sweep(endpoint.state,endpoint.positions,endpoint.tuning,eta_rng=endpoint.eta_rng,gauge_rng=endpoint.gauge_rng,master_key=endpoint.master_key,state_factor_ids=target.factor_ids,label='diagnostic-original-transition-replay')
        except Captured:pass
        else:raise RuntimeError('Requested factor not captured')
        jax.clear_caches()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--commit',required=True)
    args=parser.parse_args();run(args.plan,args.commit)
