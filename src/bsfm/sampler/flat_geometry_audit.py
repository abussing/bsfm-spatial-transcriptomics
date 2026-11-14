"""Explicit saved-conditional audit; never resumes or writes a scientific fit.

Compare inherited tuning, ordinary retuning, and retuning in variance coordinates
on exactly the same authenticated three-dimensional flat conditional.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import blackjax
import jax
import jax.numpy as jnp
import numpy as np
from . import run_inputs
from .flat_control import FlatTarget
from .run import check_repository
from .split_kernels import make_logdensity
from .variance_coordinates import to_original,to_variances,wrap_value_grad


def conditional_arm(value_grad, q, context, inherited, *, chart, retune, seed,
                    warmup_steps, draws):
    """Private RNG, fixed conditional, and fixed tuning during measurement."""
    transformed=wrap_value_grad(value_grad) if chart else value_grad
    ld_full=make_logdensity({'value_grad':transformed})
    ld=lambda p:ld_full(p,*context)
    position=to_variances(q) if chart else q
    keys=jax.random.split(jax.random.PRNGKey(seed),draws+1)
    start=time.monotonic()
    if retune:
        adapter=blackjax.window_adaptation(blackjax.nuts,ld,
            is_mass_matrix_diagonal=True,initial_step_size=.01,
            target_acceptance_rate=.9,progress_bar=False,max_num_doublings=10)
        result,history=adapter.run(keys[0],position,num_steps=warmup_steps)
        state=result.state;tuning=result.parameters
        warm=dict(acceptance=float(jnp.mean(history.info.acceptance_rate)),
                  divergences=int(jnp.sum(history.info.is_divergent)))
    else:
        state=blackjax.nuts.init(position,ld);tuning=inherited
        warm=None
    jax.block_until_ready(state.position)
    warm_seconds=time.monotonic()-start
    kernel=blackjax.nuts.build_kernel()
    def step(state,key):
        state,info=kernel(key,state,ld,tuning['step_size'],
                         tuning['inverse_mass_matrix'],max_num_doublings=10)
        original=to_original(state.position) if chart else state.position
        return state,(original,info.acceptance_rate,info.is_divergent,info.num_integration_steps)
    scan=jax.jit(lambda s,ks:jax.lax.scan(step,s,ks))
    blocks=[];start=time.monotonic()
    for j in range(0,draws,16):
        state,block=scan(state,keys[1+j:1+min(j+16,draws)])
        jax.block_until_ready(state.position);blocks.append(block)
        print('AUDIT',chart,retune,seed,min(j+16,draws),'/',draws,flush=True)
    arrays=[np.concatenate([np.asarray(b[i]) for b in blocks]) for i in range(4)]
    samples,accept,div,steps=arrays
    report=dict(chart='log_variances' if chart else 'original',retuned=retune,
        seed=seed,warmup=warm,warmup_seconds=warm_seconds,
        sampling_seconds=time.monotonic()-start,draws=draws,
        step_size=float(tuning['step_size']),inverse_mass=np.asarray(tuning['inverse_mass_matrix']).tolist(),
        acceptance=float(accept.mean()),divergences=int(div.sum()),
        median_steps=float(np.median(steps)),cap_fraction=float(np.mean(steps>=1023)),
        mean_original_coordinates=samples.mean(0).tolist(),
        sd_original_coordinates=samples.std(0).tolist(),
        scope='fixed-conditional diagnostic draws, not scientific posterior draws')
    return report,dict(positions=samples,acceptance=accept,divergent=div,leapfrogs=steps)


def run(plan_path,commit):
    plan_path=Path(plan_path);check_repository(plan_path,commit)
    plan=json.loads(plan_path.read_text());assert plan['source_commit']==commit
    root=Path(plan['output']).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()):raise ValueError('External output required')
    root.mkdir(parents=True,exist_ok=True)
    for case in plan['cases']:
        run_inputs.authenticate_files({k:case[k] for k in ('recipe','conditional','genesis','source_report')})
        recipe=json.loads(Path(case['recipe']['path']).read_text())
        if 'transition_policy' in recipe:
            raise ValueError('This inherited-tuning comparison expects original-coordinate tuning')
        if recipe['model']!='flat' or not recipe.get('flat_range_prior'):
            raise ValueError('This audit requires learned-range flat')
        run_inputs.authenticate_environment(gpu_runtime=recipe['gpu_runtime'])
        target,_,_,_=run_inputs.load_inputs(recipe['files'],recipe['factor_ids'],
            genesis_path=case['genesis']['path'],dataset_recipe=recipe['dataset_recipe'])
        target=FlatTarget(target.inputs,target.geometry,target.rule,
            factor_ids=target.factor_ids,range_prior=recipe['flat_range_prior'])
        with np.load(case['conditional']['path'],allow_pickle=False) as z:
            q=jnp.asarray(z['position']);ctx=tuple(jnp.asarray(z[k]) for k in ('u','ct','penalty'))
            inherited=dict(step_size=jnp.asarray(z['step']),inverse_mass_matrix=jnp.asarray(z['inverse_mass']))
        if q.shape!=(3,):raise ValueError('Unexpected sampled dimension')
        vg=jax.jit(target._kernels['value_grad']);changed=jax.jit(wrap_value_grad(vg))
        x=to_variances(q);v,g=changed(x,*ctx);ov,_=vg(q,*ctx)
        np.testing.assert_allclose(v+jnp.log(2.),ov,rtol=1e-10,atol=1e-8)
        errors=[]
        for direction in np.eye(3):
            errors.append(min(float(abs((changed(x+h*direction,*ctx)[0]-changed(x-h*direction,*ctx)[0])/(2*h)-g@direction)/max(1.,abs(float(g@direction)))) for h in (1e-3,3e-4,1e-4)))
        if max(errors)>1e-4:raise RuntimeError('Transformed gradient audit failed')
        for arm,chart,retune in [('inherited',False,False),('retuned',False,True),('variance',True,True)]:
            for seed in plan['seeds']:
                name=case['name']+'-'+arm+'-'+str(seed)
                if (root/(name+'.json')).exists():raise ValueError('Refuse to overwrite completed audit')
                report,arrays=conditional_arm(vg,q,ctx,inherited,chart=chart,retune=retune,seed=seed,warmup_steps=plan['warmup_steps'],draws=plan['draws'])
                report.update(case=case,source_commit=commit,gradient_errors=errors,
                    plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest())
                np.savez_compressed(root/(name+'.npz'),**arrays)
                (root/(name+'.json')).write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
                print('COMPLETE',name,json.dumps(report),flush=True)
        jax.clear_caches()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--commit',required=True)
    args=parser.parse_args();run(args.plan,args.commit)
