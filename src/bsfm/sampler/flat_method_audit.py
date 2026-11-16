"""Bounded fixed-conditional flat comparisons; never a production transition policy."""
import json
import signal
import time
from pathlib import Path
import numpy as np


def slice_one(logdensity, x, rng, *, width, max_steps, max_shrink):
    """Neal randomized finite stepping-out/shrinkage, with explicit failure."""
    if width <= 0 or max_steps < 1 or max_shrink < 1:
        raise ValueError("Positive slice controls required")
    calls = 0
    def evaluate(y):
        nonlocal calls
        calls += 1
        v = float(logdensity(y))
        if np.isnan(v) or v == np.inf:
            raise FloatingPointError("Invalid slice density")
        return v
    initial = evaluate(x)
    if not np.isfinite(initial):
        raise FloatingPointError("Nonfinite slice start")
    height = initial - rng.exponential()
    left = x - width*rng.uniform()
    right = left + width
    j = int(rng.integers(max_steps))
    k = max_steps - 1 - j
    expansions = 0
    while j > 0 and evaluate(left) > height:
        left -= width
        j -= 1
        expansions += 1
    while k > 0 and evaluate(right) > height:
        right += width
        k -= 1
        expansions += 1
    for shrinking in range(max_shrink):
        candidate = rng.uniform(left, right)
        if evaluate(candidate) >= height:
            return candidate, dict(evaluations=calls, expansions=expansions,
                                   shrinks=shrinking)
        if candidate < x:
            left = candidate
        else:
            right = candidate
    raise RuntimeError("Slice shrink limit reached; no fallback or sample emitted")


def provisional_ess(x):
    """Single-chain initial-positive-pair estimate; no convergence certification."""
    x = np.asarray(x, float)
    n = len(x)
    if n < 50:
        return None
    y = x-x.mean()
    variance = np.dot(y,y)
    if variance <= 0:
        return 0.
    fft = np.fft.rfft(y, n=2*n)
    ac = np.fft.irfft(fft*fft.conj())[:n]/variance
    pairs = []
    for i in range(0,n-1,2):
        pair = ac[i]+ac[i+1]
        if pair <= 0:
            break
        pairs.append(min(pair,pairs[-1]) if pairs else pair)
    tau = max(1., -1.+2.*sum(pairs))
    return float(min(n,n/tau))


def run(plan_path, commit):
    import jax
    import jax.numpy as jnp
    import blackjax
    from blackjax.adaptation.window_adaptation import base, build_schedule
    from . import run_inputs
    from .run import check_repository
    from .flat_control import FlatTarget
    from .flat_replay_profile import require_original_coordinates
    from .split_kernels import make_logdensity
    from .variance_coordinates import to_original, to_variances, wrap_value_grad
    from .flat_path_audit import save
    from .checkpoint_contract import digest

    check_repository(plan_path,commit)
    plan=json.loads(Path(plan_path).read_text())
    if plan["source_commit"] != commit:
        raise ValueError("Wrong frozen source")
    if not 1 <= plan["maximum_seconds"] <= 780:
        raise ValueError("At most 13 internal minutes")
    root=Path(plan["output"]).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()):
        raise ValueError("External output required")
    root.mkdir(parents=True,exist_ok=False)
    result=dict(source_commit=commit,scope="Fixed conditional diagnostic only",
                validation=[], inherited=[], chains=[], timing={})
    started=time.monotonic()
    def publish(status):
        save(root/"results.json", result)
        save(root/"status.json", dict(status=status,seconds=time.monotonic()-started))
    def expired(*_):
        raise TimeoutError("Internal diagnostic deadline")
    signal.signal(signal.SIGALRM,expired)
    signal.alarm(plan["maximum_seconds"])
    try:
        run_inputs.authenticate_files(dict(recipe=plan["recipe"],genesis=plan["genesis"]))
        recipe=json.loads(Path(plan["recipe"]["path"]).read_text())
        require_original_coordinates(recipe)
        if recipe["model"] != "flat":
            raise ValueError("Only flat captures")
        env=run_inputs.authenticate_environment(gpu_runtime=recipe["gpu_runtime"])
        result["environment_identity"]=digest(env)
        audit=[]
        target_base,_,_,_=run_inputs.load_inputs(
            recipe["files"],recipe["factor_ids"],genesis_path=plan["genesis"]["path"],
            dataset_recipe=recipe["dataset_recipe"],migration_geometry_audit=audit)
        target=FlatTarget(target_base.inputs,target_base.geometry,target_base.rule,
                          factor_ids=target_base.factor_ids,range_prior=recipe["flat_range_prior"])
        result["geometry_audit"]=audit
        states=[]
        for case in plan["cases"]:
            run_inputs.authenticate_files({k:case[k] for k in ("report","index","conditional")})
            report=json.loads(Path(case["report"]["path"]).read_text())
            index=json.loads(Path(case["index"]["path"]).read_text())
            if not index["authenticated_transition_replay"] or report["policy"] is not None:
                raise ValueError("Original authenticated replay required")
            if not all(r["comparison"]["matches_recorded_transition"] for r in report["replays"]):
                raise ValueError("Unverified replay")
            import hashlib
            identity=hashlib.sha256(target.identity.encode()).hexdigest()
            if any(row["context"]["target_sha256"] != identity for row in index["rows"]):
                raise ValueError("Captured target identity differs")
            with np.load(case["conditional"]["path"],allow_pickle=False) as z:
                states.append({k:z[k].copy() for k in z.files})
        if len(states)!=2:
            raise ValueError("Two fixed conditionals required")

        original_vg=jax.jit(target._kernels["value_grad"])
        variance_vg=jax.jit(wrap_value_grad(target._kernels["value_grad"]))
        original_ld=make_logdensity(target._kernels)
        variance_ld=make_logdensity(dict(value_grad=wrap_value_grad(target._kernels["value_grad"])))
        variance_value=jax.jit(lambda p,u,ct,penalty:variance_ld(p,u,ct,penalty))
        kernel=blackjax.nuts.build_kernel()
        methods=("original_joint","variance_joint","nugget_slice")
        transitions={}
        for method in methods:
            def transition(key,p,u,ct,penalty,step,mass,method=method):
                ld=original_ld if method=="original_joint" else variance_ld
                if method=="nugget_slice":
                    indices=jnp.array([0,2])
                    density=lambda v:ld(p.at[indices].set(v),u,ct,penalty)
                    state=blackjax.nuts.init(p[indices],density)
                else:
                    density=lambda v:ld(v,u,ct,penalty)
                    state=blackjax.nuts.init(p,density)
                new,info=kernel(key,state,density,step,mass,
                                max_num_doublings=plan["max_tree_depth"])
                end=p.at[indices].set(new.position) if method=="nugget_slice" else new.position
                return end,(info.acceptance_rate,info.is_divergent,info.num_integration_steps)
            transitions[method]=jax.jit(transition)
        ai,au,af=base(True,plan["target_acceptance"])
        au=jax.jit(au);af=jax.jit(af)
        schedule=build_schedule(plan["warmup_steps"])
        contexts=[tuple(jnp.asarray(s[k]) for k in ("u","ct","penalty")) for s in states]
        locs=np.asarray(target_base.inputs.arrays["slocs"])
        ids=np.linspace(0,len(locs)-1,16,dtype=int)
        ii,jj=np.triu_indices(16,1)
        differences=locs[ids[ii]]-locs[ids[jj]]
        order=np.argsort(np.linalg.norm(differences,axis=1))
        chosen=order[np.linspace(0,len(order)-1,7,dtype=int)[1:-1]]
        phase=differences[chosen]@np.asarray(target_base.rule.arrays["omega"]).T
        weights=np.asarray(target_base.rule.arrays["sqrt_weights"])**2
        result["covariance_pair_cell_indices"]=np.column_stack((ids[ii[chosen]],ids[jj[chosen]])).tolist()
        def summarize(draws,state,elapsed):
            q=np.asarray(draws)
            logs=2*q[:,0]-np.logaddexp(0,-q[:,1])
            logn=2*q[:,0]-np.logaddexp(0,q[:,1])
            vs=np.exp(logs);vn=np.exp(logn)
            cov=vs[:,None]*(np.cos(.14*np.exp(-q[:,2,None,None])*phase[None,:,:])@weights)
            diag=vs*weights.sum()+vn
            values=np.column_stack((logs,logn,q[:,2],diag,cov))
            names=["log_spatial_variance","log_nugget_variance","log_range","covariance_diagonal"]+[f"covariance_pair_{i}" for i in range(len(chosen))]
            metrics={}
            for name,x in zip(names,values.T):
                ess=provisional_ess(x)
                metrics[name]=dict(mean=float(x.mean()),sd=float(x.std()),
                    quantiles=np.quantile(x,[.05,.5,.95]).tolist(),provisional_ess=ess,
                    provisional_ess_per_second=None if ess is None else ess/elapsed)
            u,count=np.unique(state["u"],return_counts=True)
            ratio=vn[:,None]*u[None,:]
            fisher=.5*((ratio/(1+ratio))**2@count)
            z=1/(1+np.exp(-q[:,1]))
            D=state["inverse_mass"]
            number=float(state["step"])*np.sqrt(fisher*(4*D[0]+z*z*D[1]))
            return metrics,values,dict(min=float(number.min()),max=float(number.max()),
                median=float(np.median(number)),meaning="Nugget approximation using original inherited tuning, not a stability bound")
        # Value, Jacobian and independent density finite-difference checks on REAL states.
        for index,(state,context) in enumerate(zip(states,contexts)):
            rows=[]
            for shift in [np.zeros(3),np.array([.08,-.2,.015]),np.array([-.08,.2,-.015])]:
                q=jnp.asarray(state["position"]+shift)
                v=to_variances(q)
                fo,go=original_vg(q,*context)
                fv,gv=variance_vg(v,*context)
                if abs(float(variance_value(v,*context))-float(fv))>1e-8:
                    raise RuntimeError("Value-only slice density differs")
                jac=np.asarray(jax.jacfwd(to_original)(v))
                fd=[]
                for e in np.eye(3)*1e-5:
                    fp=float(variance_vg(v+e,*context)[0])
                    fm=float(variance_vg(v-e,*context)[0])
                    fd.append((fp-fm)/2e-5)
                err=float(np.max(np.abs(np.asarray(gv)-fd)/np.maximum(1.,np.abs(fd))))
                row=dict(value_error=float(abs(fv-fo+np.log(2.))),
                         roundtrip=float(np.max(np.abs(np.asarray(to_original(v)-q)))),
                         jacobian_error=float(abs(abs(np.linalg.det(jac))-.5)),
                         gradient_pullback_error=float(np.max(np.abs(np.asarray(gv)-jac.T@np.asarray(go)))),
                         finite_difference_scaled_error=err)
                rows.append(row)
            result["validation"].append(dict(case=index,checks=rows))
        if any(r["value_error"]>1e-8 or r["roundtrip"]>1e-10 or r["jacobian_error"]>1e-10
               or r["gradient_pullback_error"]>1e-7 or r["finite_difference_scaled_error"]>2e-4
               for group in result["validation"] for r in group["checks"]):
            raise RuntimeError("Real-state target validation failed")
        publish("target_verified")
        print("TARGET_VERIFIED",flush=True)
        if plan.get("mode")=="reference":
            from .conditional_reference import conditional_reference
            result["reference"]=[]
            for index,(state,context) in enumerate(zip(states,contexts)):
                def vg(q):
                    return original_vg(jnp.asarray(q),*context)
                starts=[state["position"]+np.asarray(offset) for offset in plan["start_offsets"]]
                summary,points,weights_ref=conditional_reference(vg,starts,
                    seed=plan["seed"]+100*index,power=plan["reference_power"])
                name=f"reference-case{index}.npz"
                np.savez_compressed(root/name,original_positions=points,weights=weights_ref)
                result["reference"].append(dict(case=index,file=name,**summary))
                publish("reference_case_complete")
                print("REFERENCE",index,"COMPLETE",flush=True)
            publish("complete")
            return
        # Compile each shape once; excluded from sampling times and samples.
        compile_start=time.monotonic()
        for method in methods:
            q=jnp.asarray(states[0]["position"])
            p=q if method=="original_joint" else to_variances(q)
            dim=2 if method=="nugget_slice" else 3
            end,_=transitions[method](jax.random.PRNGKey(1),p,*contexts[0],.01,jnp.ones(dim))
            jax.block_until_ready(end)
            ads=ai(p[jnp.array([0,2])] if dim==2 else p,.01)
            ads=au(ads,schedule[0],p[jnp.array([0,2])] if dim==2 else p,.9)
            jax.block_until_ready(af(ads))
        result["timing"]["compile_seconds"]=time.monotonic()-compile_start

        def run_chain(case,method,start_index,inherited=False):
            context=contexts[case];state=states[case]
            q=jnp.asarray(state["position"]+np.asarray(plan["start_offsets"][start_index]))
            p=q if method=="original_joint" else to_variances(q)
            seed=plan["seed"]+1000*case+100*methods.index(method)+10*start_index
            key=jax.random.PRNGKey(seed);srng=np.random.default_rng(seed+1)
            evals=0;warm_rows=[];draws=[];rows=[]
            def update(p,step,mass):
                nonlocal key,evals
                key,sub=jax.random.split(key)
                cost=dict(evaluations=0,expansions=0,shrinks=0)
                if method=="nugget_slice":
                    def scalar(x):
                        return variance_value(p.at[1].set(x),*context)
                    x,cost=slice_one(scalar,float(p[1]),srng,
                        width=plan["slice_width"],max_steps=plan["slice_max_steps"],
                        max_shrink=plan["slice_max_shrink"])
                    p=p.at[1].set(x)
                p,info=transitions[method](sub,p,*context,step,mass)
                jax.block_until_ready(p)
                ac,dv,lf=map(np.asarray,info)
                evals+=cost["evaluations"]+int(lf)+1
                return p,dict(acceptance=float(ac),divergent=bool(dv),leapfrogs=int(lf),**cost)
            warm_start=time.monotonic()
            if inherited:
                step=jnp.asarray(state["step"]);mass=jnp.asarray(state["inverse_mass"])
            else:
                indices=jnp.array([0,2]) if method=="nugget_slice" else jnp.arange(3)
                ads=ai(p[indices],plan["initial_step"])
                for i in range(plan["warmup_steps"]):
                    if time.monotonic()-warm_start>plan["warmup_seconds"]:
                        return dict(case=case,method=method,start=start_index,
                                    status="warmup_budget_exhausted",warmup=warm_rows,
                                    warmup_seconds=time.monotonic()-warm_start)
                    p,row=update(p,ads.step_size,ads.inverse_mass_matrix)
                    warm_rows.append(row)
                    ac=min(1.,row["acceptance"])
                    if not np.isfinite(ac):
                        raise FloatingPointError("Nonfinite NUTS acceptance")
                    ads=au(ads,schedule[i],p[indices],ac)
                step,mass=af(ads)
            warm_seconds=time.monotonic()-warm_start
            start=time.monotonic();evals_before=evals
            limit=plan["inherited_draws"] if inherited else plan["maximum_draws"]
            while len(draws)<limit and time.monotonic()-start<plan["sampling_seconds"]:
                p,row=update(p,step,mass)
                original=p if method=="original_joint" else to_original(p)
                draws.append(np.asarray(original));rows.append(row)
            elapsed=time.monotonic()-start
            tag=f"case{case}-{method}-start{start_index}"+("-inherited" if inherited else "")
            metrics,monitors,stiffness=summarize(draws,state,elapsed)
            np.savez_compressed(root/(tag+".npz"),original_positions=np.asarray(draws),
                                covariance_and_logvariance_monitors=monitors)
            return dict(case=case,method=method,start=start_index,status="complete",
                        inherited=inherited,draw_file=tag+".npz",draws=len(draws),
                        warmup_seconds=warm_seconds,sampling_seconds=elapsed,
                        evaluations=evals-evals_before,step=float(step),inverse_mass=np.asarray(mass).tolist(),
                        warmup=warm_rows,sampling=rows,metrics=metrics,stiffness=stiffness)

        for case in range(2):
            result["inherited"].append(run_chain(case,"original_joint",0,True))
            publish("inherited_complete")
        for start_index in range(len(plan["start_offsets"])):
            for case in range(2):
                for method in methods:
                    row=run_chain(case,method,start_index)
                    result["chains"].append(row)
                    publish("chain_complete")
                    print("CHAIN",case,method,start_index,row["status"],row.get("draws"),flush=True)
        publish("complete")
    except Exception as exc:
        result["error"]=dict(type=type(exc).__name__,message=str(exc))
        publish("stopped")
        raise
    finally:
        signal.alarm(0)

