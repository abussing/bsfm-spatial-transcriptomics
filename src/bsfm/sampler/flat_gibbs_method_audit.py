"""Bounded full-Gibbs diagnostic from one frozen checkpoint, never a fit continuation."""
import copy
import json
import signal
import time
from pathlib import Path
import numpy as np
import jax
import jax.numpy as jnp
from . import run_inputs, layer6
from .run import check_repository
from .run_checkpoint_fork import source_endpoint
from .checkpoint_contract import digest
from .flat_control import FlatTarget, FlatTransition
from .coordinate_transition import VarianceTransition
from .diagnostic_nugget_slice import DiagnosticNuggetSlice
from .layer4 import JointEtaConditional
from .flat_path_audit import save


def run(plan_path,commit):
    check_repository(plan_path,commit)
    plan=json.loads(Path(plan_path).read_text())
    if plan["source_commit"]!=commit or not 1<=plan["maximum_seconds"]<=780:
        raise ValueError("Frozen source and bounded diagnostic required")
    root=Path(plan["output"]).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()):raise ValueError("External output")
    root.mkdir(parents=True,exist_ok=False)
    result=dict(source_commit=commit,arms=[],scope="Diagnostic; no scientific posterior deliverable")
    started=time.monotonic()
    def publish(status):
        save(root/"results.json",result)
        save(root/"status.json",dict(status=status,seconds=time.monotonic()-started))
    def expired(*_):raise TimeoutError("Whole diagnostic time limit")
    signal.signal(signal.SIGALRM,expired);signal.alarm(plan["maximum_seconds"])
    try:
        run_inputs.authenticate_files(plan["gates"])
        gate=json.load(open(plan["gates"]["summary"]["path"]))
        if gate["status"]["status"]!="complete" or len(gate["groups"])!=6:
            raise ValueError("Fixed-conditional comparison incomplete")
        for row in gate["groups"]:
            if row["completed_starts"]!=2 or row["divergences"] or max(row["split_rhat"])>1.05:
                raise ValueError("Fixed-conditional gate failed")
            if row["largest_start_mean_error_reference_sd"]>.3:
                raise ValueError("Reference agreement gate failed")
        for row in gate["reference"]:
            reps=row["integration"]
            if min(r["weight_ess"] for r in reps)<1000 or max(r["maximum_weight"] for r in reps)>.005:
                raise ValueError("Independent reference quality gate failed")
            if abs(reps[0]["log_normalizer"]-reps[1]["log_normalizer"])>.01:
                raise ValueError("Independent reference replicates disagree")
        case=plan["case"]
        run_inputs.authenticate_files(dict(recipe=case["recipe"],**case["source"]))
        recipe=json.load(open(case["recipe"]["path"]))
        if recipe.get("transition_policy") is not None or recipe["model"]!="flat":
            raise ValueError("Original flat source checkpoint required")
        env=run_inputs.authenticate_environment(gpu_runtime=recipe["gpu_runtime"])
        geometry_audit=[]
        base,loading,eta,_=run_inputs.load_inputs(recipe["files"],recipe["factor_ids"],
            genesis_path=case["source"]["genesis"]["path"],dataset_recipe=recipe["dataset_recipe"],
            migration_geometry_audit=geometry_audit)
        target=FlatTarget(base.inputs,base.geometry,base.rule,factor_ids=base.factor_ids,
                          range_prior=recipe["flat_range_prior"])
        endpoint,binding=source_endpoint(case["source"],target,loading,eta,seed=recipe["seed"],
            environment_identity=digest(env),output=root,runtime_migration=case.get("runtime_migration"))
        result.update(source=binding,geometry_audit=geometry_audit,factors=len(target.factor_ids))
        locs=np.asarray(target.inputs.arrays["slocs"])
        idx=np.linspace(0,len(locs)-1,12,dtype=int)
        phase=(locs[idx[:6]]-locs[idx[6:]])@np.asarray(target.rule.arrays["omega"]).T
        weights=np.asarray(target.rule.arrays["sqrt_weights"])**2
        def covariance_monitor(q):
            a2=np.exp(2*q[0]);z=1/(1+np.exp(-q[1]))
            off=a2*z*(np.cos(.14*np.exp(-q[2])*phase)@weights)
            return np.r_[a2*(z*weights.sum()+1-z),off]
        for method in plan["methods"]:
            ep=copy.deepcopy(endpoint)
            layer=layer6.GibbsSweep(target,b_sigma2=ep.b_sigma2)
            layer.joint_eta=JointEtaConditional(target,maximum_iterations=recipe.get("pcg_maximum_iterations",320))
            if method=="original_joint":transition=FlatTransition(target)
            elif method=="variance_joint":transition=VarianceTransition(target,dict(name="flat_variances_v1"))
            elif method=="nugget_slice":transition=DiagnosticNuggetSlice(target,depth=10)
            else:raise ValueError("Unknown diagnostic arm")
            layer.split=transition
            arm=dict(method=method,tuning=[],sweeps=[],factor_calls=[],
                     initialization="Identical checkpoint; tune each initial conditional, then restore original starting state",
                     state_hashes=layer6.state_hashes(ep.state),positions=[p.values.tolist() for p in ep.positions])
            result["arms"].append(arm);publish("arm_started")
            arm_start=time.monotonic();tunings=[]
            for i,position in enumerate(ep.positions):
                key=jax.random.fold_in(ep.master_key,10000+i)
                t=time.monotonic()
                if method=="nugget_slice":
                    tuning,history=transition.fit_tuning(key,position,ep.state,
                        steps=plan["warmup_steps"],maximum_seconds=60)
                    divergences=sum(x["divergent"] for x in history)
                else:
                    adapted=transition.adapt(key,position,ep.state,state_factor_ids=target.factor_ids,
                                             steps=plan["warmup_steps"])
                    tuning=adapted.tuning
                    divergences=int(np.asarray(adapted.history.info.is_divergent).sum())
                tunings.append(tuning)
                arm["tuning"].append(dict(factor=i,seconds=time.monotonic()-t,
                    step=tuning.step_size,inverse_mass=tuning.inverse_mass_matrix.tolist(),
                    warmup_divergences=divergences))
                publish("tuning_factor_complete")
                if time.monotonic()-arm_start>plan["arm_seconds"]:
                    break
            if len(tunings)!=len(ep.positions):
                arm["status"]="tuning_budget_exhausted";publish("arm_incomplete");continue
            original=transition.transition
            sweep_number=0
            def observed(key,position,state,tuning,**kwargs):
                context=kwargs["prepared_context"]
                q=position.values;z=1/(1+np.exp(-q[1]))
                vn=np.exp(2*q[0])*(1-z);ratio=vn*np.asarray(context.u)
                F=.5*np.sum((ratio/(1+ratio))**2)
                t=time.monotonic()
                out=original(key,position,state,tuning,**kwargs)
                jax.block_until_ready(out.nuts_state.position)
                changed=out.position.values
                factor=target.factor_ids.index(position.factor_id)
                inherited=ep.tuning[factor]
                D=inherited.inverse_mass_matrix
                inherited_number=inherited.step_size*np.sqrt(F*(4*D[0]+z*z*D[1]))
                native_number=None
                if method=="original_joint":
                    D=tuning.inverse_mass_matrix
                    native_number=tuning.step_size*np.sqrt(F*(4*D[0]+z*z*D[1]))
                elif method=="variance_joint":
                    native_number=tuning.step_size*np.sqrt(F*tuning.inverse_mass_matrix[1])
                before_cov=covariance_monitor(q);after_cov=covariance_monitor(changed)
                row=dict(sweep=sweep_number,factor=target.factor_ids.index(position.factor_id),
                    position_before=q.tolist(),position_after=changed.tolist(),
                    nugget_expected_information=float(F),
                    inherited_nugget_step_number=float(inherited_number),
                    native_nugget_step_number=None if native_number is None else float(native_number),
                    covariance_relative_change=float(np.linalg.norm(after_cov-before_cov)/max(np.linalg.norm(before_cov),1e-30)),
                    median_nugget_u=float(np.median(ratio)),
                    elapsed=time.monotonic()-t,acceptance=float(out.info.acceptance_rate),
                    divergent=bool(out.info.is_divergent),leapfrogs=int(out.info.num_integration_steps),
                    slice_cost=out.audit.get("slice_cost"))
                arm["factor_calls"].append(row)
                publish("factor_complete")
                return out
            transition.transition=observed
            state=ep.state;positions=ep.positions;master=ep.master_key
            np.random.set_state(ep.numpy_global_state)
            for sweep_number in range(1,plan["sweeps"]+1):
                if time.monotonic()-arm_start>plan["arm_seconds"]:break
                t=time.monotonic()
                out=layer.sweep(state,positions,tuple(tunings),eta_rng=ep.eta_rng,
                    gauge_rng=ep.gauge_rng,master_key=master,state_factor_ids=target.factor_ids,
                    label="bounded-flat-method-diagnostic")
                state=out.state;positions=out.positions;master=out.master_key
                row=dict(sweep=sweep_number,seconds=time.monotonic()-t,
                    positions=[p.values.tolist() for p in positions],
                    alpha=state.alpha.tolist(),zeta=state.zeta.tolist(),
                    sigma2=state.sigma2.tolist(),factor_order=list(out.factor_order),
                    fitted_Y_sha256=out.audit["fitted_Y_sha256"],
                    pcg_diagnostics=[str(d) for d in out.pcg_diagnostics])
                arm["sweeps"].append(row)
                publish("sweep_complete")
                print("SWEEP",method,sweep_number,round(row["seconds"],3),flush=True)
            arm["status"]="complete" if len(arm["sweeps"])==plan["sweeps"] else "arm_budget_exhausted"
            arm["seconds"]=time.monotonic()-arm_start
            publish("arm_complete")
        publish("complete" if all(a.get("status")=="complete" for a in result["arms"]) else "bounded_partial")
    except Exception as exc:
        result["error"]=dict(type=type(exc).__name__,message=str(exc));publish("stopped");raise
    finally:signal.alarm(0)

