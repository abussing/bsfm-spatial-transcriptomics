"""Bounded flat-transition replay and synchronized timings; no retuning or fits."""
import argparse
import contextlib
import copy
import json
import signal
import time
from pathlib import Path
import jax
import jax.numpy as jnp
import numpy as np
from . import run_inputs, layer6
from .boundary_diagnostics import BoundaryRecorder
from .checkpoint_contract import digest
from .flat_control import FlatTarget, FlatTransition
from .layer4 import JointEtaConditional
from .run import check_repository
from .run_checkpoint_fork import source_endpoint

def synchronize(value):
    """Wait for device leaves, including result dataclasses, before timing stops."""
    if hasattr(value, "__dataclass_fields__"):
        for name in value.__dataclass_fields__: synchronize(getattr(value, name))
    elif isinstance(value, dict):
        for item in value.values(): synchronize(item)
    elif isinstance(value, (tuple, list)):
        for item in value: synchronize(item)
    elif hasattr(value, "block_until_ready"):
        value.block_until_ready()

@contextlib.contextmanager
def timed_calls(bindings, rows):
    """Instrument temporary call sites without changing arguments or outputs."""
    originals = []
    try:
        for obj, name, label in bindings:
            original = getattr(obj, name)
            originals.append((obj, name, original))
            def measured(*args, _fn=original, _label=label, **kwargs):
                start = time.perf_counter()
                result = _fn(*args, **kwargs)
                synchronize(result)
                rows.append(dict(operation=_label, seconds=time.perf_counter()-start))
                return result
            setattr(obj, name, measured)
        yield
    finally:
        for obj, name, original in reversed(originals): setattr(obj, name, original)

def compare_diagnostics(actual, expected):
    same = (np.allclose(actual['acceptance'], expected['acceptance'], rtol=1e-9, atol=1e-11)
            and np.array_equal(actual['divergent'], expected['divergent'])
            and np.array_equal(actual['leapfrogs'], expected['leapfrogs']))
    return dict(matches_recorded_transition=bool(same),
                max_acceptance_difference=float(np.max(np.abs(
                    np.asarray(actual['acceptance'])-np.asarray(expected['acceptance'])))))

def write(path, value):
    tmp = path.with_suffix(path.suffix+'.partial')
    tmp.write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    tmp.replace(path)

def require_original_coordinates(recipe):
    if recipe.get('transition_policy') is not None:
        raise ValueError('Original flat coordinates required; experimental policies are excluded')

def run(plan_path, commit):
    check_repository(plan_path, commit)
    plan=json.loads(Path(plan_path).read_text())
    if plan['source_commit'] != commit: raise ValueError('Wrong source commit')
    root=Path(plan['output']).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()): raise ValueError('External output required')
    root.mkdir(parents=True, exist_ok=False)
    deadline=int(plan['maximum_seconds'])
    if not 1 <= deadline <= 2400: raise ValueError('At most 40 minutes inside allocation')
    def timeout(*_): raise TimeoutError('Diagnostic wall-clock budget reached')
    signal.signal(signal.SIGALRM, timeout); signal.alarm(deadline)
    write(root/'status.json',dict(status='started',scientific_draws=False))
    try:
        for case in plan['cases']:
            dest=root/case['name']; dest.mkdir()
            run_inputs.authenticate_files(dict(recipe=case['recipe'],expected=case['expected'],**case['source']))
            recipe=json.loads(Path(case['recipe']['path']).read_text())
            if recipe['model'] != 'flat': raise ValueError('Flat only')
            policy=recipe.get('transition_policy')
            require_original_coordinates(recipe)
            env=run_inputs.authenticate_environment(gpu_runtime=recipe['gpu_runtime'])
            from .run_gpu_environment import preflight_gpu_callback
            preflight_gpu_callback()
            migration=case.get('runtime_migration')
            geometry_audit=[] if migration else None
            base,loading,eta,_=run_inputs.load_inputs(recipe['files'],recipe['factor_ids'],
                genesis_path=case['source']['genesis']['path'],dataset_recipe=recipe['dataset_recipe'],
                migration_geometry_audit=geometry_audit)
            target=FlatTarget(base.inputs,base.geometry,base.rule,factor_ids=base.factor_ids,
                              range_prior=recipe['flat_range_prior'])
            endpoint,binding=source_endpoint(case['source'],target,loading,eta,seed=recipe['seed'],
                environment_identity=digest(env),output=dest,runtime_migration=migration)
            if case['sweep'] != binding['completed_sweep']+1: raise ValueError('Next sweep required')
            source_inputs=json.loads(Path(case['source']['inputs']['path']).read_text())
            require_original_coordinates(source_inputs)
            layer=layer6.GibbsSweep(target,b_sigma2=endpoint.b_sigma2)
            layer.joint_eta=JointEtaConditional(target,maximum_iterations=recipe.get('pcg_maximum_iterations',320))
            layer.split=FlatTransition(target)
            idx=case['factor']-1
            expected=next(r for r in json.loads(Path(case['expected']['path']).read_text()) if r['sweep']==case['sweep'])
            expected=next(f for f in expected['factors'] if f['index']==idx)
            report=dict(case=case,source_commit=commit,source=binding,geometry_import=geometry_audit,
                        policy=policy,expected=expected,replays=[],scope='Diagnostic only; no adaptation or posterior continuation')
            write(dest/'report.json',report)
            original=layer.split.transition
            class Captured(Exception): pass
            captured={}
            for repetition in range(2):
                ep=copy.deepcopy(endpoint); timings=[]
                recorder=BoundaryRecorder(target,idx,ep.tuning[idx],dest/'boundaries') if repetition==1 else None
                def capture(key,position,state,tuning,**kwargs):
                    start=time.perf_counter()
                    result=original(key,position,state,tuning,**kwargs)
                    synchronize(result)
                    timings.append(dict(operation='nuts',factor=position.factor_id,seconds=time.perf_counter()-start))
                    if position.factor_id != target.factor_ids[idx]: return result
                    c=kwargs['prepared_context']
                    actual=dict(acceptance=np.asarray(result.info.block_acceptance).tolist(),
                        divergent=np.asarray(result.info.block_divergent).tolist(),
                        leapfrogs=np.asarray(result.info.block_leapfrogs).tolist())
                    comparison=compare_diagnostics(actual,expected)
                    if recorder: recorder.publish(authenticated=comparison['matches_recorded_transition'])
                    captured.update(position=np.asarray(position.values),u=np.asarray(c.u),ct=np.asarray(c.ct),
                        penalty=np.asarray(c.penalty),inverse_mass=np.asarray(tuning.inverse_mass_matrix),
                        step=np.asarray(tuning.step_size),momentum=np.asarray(result.info.momentum),key=np.asarray(key),
                        proposed_position=np.asarray(result.position.values))
                    np.savez_compressed(dest/('conditional-%s.npz'%repetition),**captured)
                    report['replays'].append(dict(repetition=repetition,actual=actual,comparison=comparison,
                        timings=timings,includes_first_compilation=repetition==0,
                        timing_scope='Gibbs prefix through selected factor, not an entire sweep; observer/storage overhead excluded from operation timers'))
                    write(dest/'report.json',report)
                    print('CAPTURED',case['name'],repetition,actual,comparison,flush=True)
                    raise Captured()
                layer.split.transition=capture
                bindings=[(layer6,n,n) for n in ['sample_Lambda_twostage','sample_sigma2_twostage',
                    'sample_phi','sample_delta_tau','refresh_alpha_gauge']]
                bindings += [(layer,'_joint_eta','joint_eta'),(target,'draw_eta','single_eta'),
                             (layer.split,'prepare_context','prepare_context')]
                np.random.set_state(ep.numpy_global_state)
                try:
                    with timed_calls(bindings,timings):
                        layer.sweep(ep.state,ep.positions,ep.tuning,eta_rng=ep.eta_rng,gauge_rng=ep.gauge_rng,
                            master_key=ep.master_key,state_factor_ids=target.factor_ids,
                            label='flat-short-replay',observer=recorder)
                except Captured: pass
                else: raise RuntimeError('Selected transition not reached')
            a,b=report['replays']
            report['repeat_diagnostics']=compare_diagnostics(a['actual'],b['actual'])
            with np.load(dest/'conditional-0.npz') as first:
                report['repeat_max_array_differences']={k:float(np.max(np.abs(first[k]-captured[k])))
                    for k in captured if k!='key'}
            # Original coordinates: log amplitude, logit spatial fraction, log range.
            full=target._kernels['value_grad']
            x=jnp.asarray(captured['position'])
            u,ct,penalty=(jnp.asarray(captured[k]) for k in ['u','ct','penalty'])
            vg=jax.jit(lambda x:full(x,u,ct,penalty))
            t=time.perf_counter(); value,grad=vg(x); synchronize((value,grad))
            report['gradient_compile_and_first_seconds']=time.perf_counter()-t
            seconds=[]
            for _ in range(5):
                t=time.perf_counter(); synchronize(vg(x)); seconds.append(time.perf_counter()-t)
            report['gradient_warm_seconds']=seconds
            report['gradient_checks']=[]
            for i in range(3):
                tests=[]
                for eps in [1e-4,3e-5]:
                    di=jnp.eye(3)[i]*eps
                    fd=float((vg(x+di)[0]-vg(x-di)[0])/(2*eps))
                    tests.append(dict(epsilon=eps,scaled_error=abs(fd-float(grad[i]))/max(1.,abs(float(grad[i])))))
                report['gradient_checks'].append(tests)
            write(dest/'report.json',report)
            write(root/'status.json',dict(status='case_complete',case=case['name']))
            jax.clear_caches()
        write(root/'status.json',dict(status='complete',scientific_draws=False))
    except Exception as exc:
        write(root/'status.json',dict(status='stopped',error=type(exc).__name__,message=str(exc)))
        raise
    finally:
        signal.alarm(0)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True);p.add_argument('--commit',required=True)
    args=p.parse_args();run(args.plan,args.commit)

