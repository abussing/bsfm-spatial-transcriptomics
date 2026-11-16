"""Read-only original-flat curvature and matched finite-duration integration probes."""
import argparse
import copy
import hashlib
import html
import itertools
import json
import signal
from pathlib import Path
import numpy as np


def curvature(vg, q, inverse_mass, step, delta=1e-4):
    """FD Hessian of negative log density; D is BlackJAX inverse mass, not mass."""
    q=np.asarray(q,float);d=np.asarray(inverse_mass,float)
    if q.shape != (3,) or d.shape != (3,) or not np.all(d>0):
        raise ValueError('Three original coordinates and positive diagonal inverse mass required')
    cols=[]
    for e in np.eye(3)*delta:
        vp,gp=vg(q+e);vm,gm=vg(q-e)
        if not np.isfinite([vp,vm]).all() or not np.isfinite([gp,gm]).all():
            raise FloatingPointError('Nonfinite Hessian stencil')
        cols.append(-(np.asarray(gp)-np.asarray(gm))/(2*delta))
    raw=np.column_stack(cols);h=(raw+raw.T)/2
    root=np.sqrt(d);scaled=root[:,None]*h*root[None,:]
    eigenvalues,eigenvectors=np.linalg.eigh(scaled)
    direction=root*eigenvectors[:,-1];direction/=np.linalg.norm(direction)
    return dict(hessian=h.tolist(),mass_scaled_eigenvalues=eigenvalues.tolist(),
                mass_scaled_eigenvectors=eigenvectors.tolist(),leading_q_direction=direction.tolist(),
                local_step_number=float(abs(step)*np.sqrt(max(0.,eigenvalues[-1]))),
                hessian_asymmetry=float(np.linalg.norm(raw-raw.T)/max(1.,np.linalg.norm(raw))),
                condition_number=float(eigenvalues[-1]/eigenvalues[0]) if eigenvalues[0]>0 else None,
                negative_curvature=bool(eigenvalues[0]<0),finite_difference_delta=delta)


def probe(vg,q,momentum,inverse_mass,step,steps,delta=1e-4):
    """Ordinary leapfrog diagnostic, not an actual adaptive NUTS tree or sampler."""
    q=np.array(q,float,copy=True);p=np.array(momentum,float,copy=True);d=np.asarray(inverse_mass,float)
    v,g=vg(q);v=float(v);g=np.asarray(g,float)
    if not np.isfinite(v) or not np.isfinite(g).all():raise ValueError('Nonfinite starting density')
    h0=-v+.5*np.dot(p,d*p);rows=[];failed=None
    for t in range(steps+1):
        if t:
            p=p+.5*step*g;q=q+step*d*p;v,g=vg(q);v=float(v);g=np.asarray(g,float)
            if not np.isfinite(v) or not np.isfinite(g).all() or not np.isfinite(q).all():
                failed=dict(step=t,reason='nonfinite trajectory');break
            p=p+.5*step*g
        error=float(-v+.5*np.dot(p,d*p)-h0)
        row=dict(step=t,time=float(t*step),q=q.tolist(),energy_error=error,gradient=g.tolist())
        try:row['curvature']=curvature(vg,q,d,step,delta)
        except FloatingPointError as exc:row['curvature_error']=str(exc)
        rows.append(row)
    return dict(rows=rows,failure=failed,step_size=float(step),requested_steps=steps,
                integration_duration=float(step*steps),momentum=np.asarray(momentum).tolist(),
                max_abs_energy_error=max(abs(r['energy_error']) for r in rows),
                max_local_step_number=max((r['curvature']['local_step_number'] for r in rows if 'curvature' in r),default=None))


def swapped(first,second,keys):
    result={k:np.array(v,copy=True) for k,v in first.items()}
    for key in keys:
        if key=='alpha_only':result['position'][0]=second['position'][0]
        elif key in ('position','u','ct','penalty'):result[key]=np.array(second[key],copy=True)
        else:raise ValueError('Unknown swap component')
    return result


def clean(value):
    if isinstance(value,dict):return {k:clean(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [clean(v) for v in value]
    if isinstance(value,np.ndarray):return clean(value.tolist())
    if isinstance(value,(float,np.floating)):return float(value) if np.isfinite(value) else None
    if isinstance(value,np.integer):return int(value)
    return value


def save(path,value):
    tmp=path.with_suffix(path.suffix+'.partial');tmp.write_text(json.dumps(clean(value),indent=2,allow_nan=False)+'\n');tmp.replace(path)


def trace_svg(path,key,label):
    values=[r['energy_error'] if key=='energy' else r.get('curvature',{}).get('local_step_number') for r in path['rows']]
    finite=[v for v in values if v is not None and np.isfinite(v)]
    if not finite:return '<p>No finite '+label+'</p>'
    lo=min(0.,min(finite));hi=max(2. if key!='energy' else 0.,max(finite));span=max(hi-lo,1e-12)
    points=' '.join(f'{45+650*i/max(1,len(values)-1):.2f},{175-145*(v-lo)/span:.2f}' for i,v in enumerate(values) if v is not None and np.isfinite(v))
    reference=f'<line x1="45" x2="695" y1="{175-145*(2-lo)/span:.2f}" y2="{175-145*(2-lo)/span:.2f}" stroke="gray" stroke-dasharray="4 4"/>' if key!='energy' else ''
    return f'<svg viewBox="0 0 730 210"><text x="45" y="18">{label}: {min(finite):.3g} to {max(finite):.3g}</text>{reference}<polyline points="{points}" fill="none" stroke="#2166ac" stroke-width="2"/><text x="45" y="202">Integration step 0 to {len(values)-1}</text></svg>'


def render(root,result):
    parts=['<!doctype html><meta charset="utf-8"><title>Original flat integration audit</title><style>body{font:16px system-ui;max-width:1100px;margin:30px auto}table{border-collapse:collapse}td,th{padding:8px;border-bottom:1px solid #ddd}svg{width:48%}section{margin:32px 0}small{color:#555}</style><h1>Original flat integration audit</h1>',
           '<p>Read-only probes of log amplitude, logit spatial fraction and log range. No retuning, new coordinates or scientific draws. The dashed value 2 is the positive quadratic leapfrog stability boundary, not a universal nonlinear threshold. Paths are fixed-duration probes, not the adaptive NUTS tree.</p>',
           '<p>Hybrid input swaps may not correspond to a realizable Gibbs state. Attribution requires agreement with actual adjacent-update snapshots. The full density includes the loading penalty and all priors.</p>']
    parts.append('<h2>Matched early/late input swaps</h2><table><tr><th>Late-state inputs substituted</th><th>Largest |ΔH|</th><th>Largest ε√λ</th><th>Nonfinite paths</th></tr>')
    for arm in result.get('swaps',[]):
        paths=arm['paths'];ener=max(p['max_abs_energy_error'] for p in paths);lam=max((p['max_local_step_number'] or 0) for p in paths)
        parts.append(f'<tr><td>{html.escape(arm["name"])}</td><td>{ener:.5g}</td><td>{lam:.5g}</td><td>{sum(p["failure"] is not None for p in paths)}</td></tr>')
    parts.append('</table><h2>Actual update snapshots</h2><table><tr><th>State/update</th><th>Local ε√λ</th><th>Native-start |ΔH|</th><th>Common-start |ΔH|</th></tr>')
    for row in result.get('boundaries',[]):
        lam=row['curvature'][0]['local_step_number']
        parts.append(f'<tr><td>{html.escape(row["name"])}</td><td>{lam:.5g}</td><td>{row["native"]["max_abs_energy_error"]:.5g}</td><td>{row["common_start"]["max_abs_energy_error"]:.5g}</td></tr>')
    parts.append('</table>')
    for arm in result.get('swaps',[]):
        if arm['name'] not in ('early_baseline','position+u+ct+penalty'):continue
        parts.append('<h2>'+html.escape(arm['name'])+'</h2>')
        for i,path in enumerate(arm['paths']):
            parts.append(f'<section><h3>Matched momentum/direction {i+1}</h3>'+trace_svg(path,'energy','Hamiltonian error')+trace_svg(path,'curvature','Local stability number')+'</section>')
    for panel in result.get('slices',[]):
        a=np.array(panel['relative_logdensity']);a=np.maximum(-50,np.minimum(0,a));n=a.shape[0];cells=[]
        for i in range(n):
            for j in range(n):
                t=(a[i,j]+50)/50;t=0 if not np.isfinite(t) else t
                color=f'rgb({int(245-210*t)},{int(245-145*t)},{int(245-80*t)})'
                cells.append(f'<rect x="{40+16*j}" y="{30+16*(n-1-i)}" width="16" height="16" fill="{color}"/>')
        parts.append('<section><h3>'+html.escape(panel['name'])+'</h3><p>Full conditional slice; other coordinate fixed at the saved starting value. Color: panel maximum (dark), to 50 log units below (pale). No mode or marginal-density claim.</p><svg viewBox="0 0 480 480">'+''.join(cells)+f'<text x="40" y="455">x: {panel["x_name"]}; y: log range</text></svg></section>')
    (root/'report.html').write_text(''.join(parts))


def run(plan_path,commit):
    import jax
    import jax.numpy as jnp
    from . import run_inputs
    from .run import check_repository
    from .flat_control import FlatTarget
    from .flat_replay_profile import require_original_coordinates
    from .contracts import logical_hash
    from .checkpoint_contract import digest
    check_repository(plan_path,commit);plan=json.loads(Path(plan_path).read_text())
    if plan['source_commit']!=commit:raise ValueError('Wrong commit')
    root=Path(plan['output']).resolve()
    if root.is_relative_to(run_inputs.REPO.resolve()):raise ValueError('External output required')
    root.mkdir(parents=True,exist_ok=False)
    budget=plan['maximum_seconds']
    if not 1<=budget<=2400:raise ValueError('Bounded diagnostic required')
    def expired(*_):raise TimeoutError('Diagnostic time budget reached')
    signal.signal(signal.SIGALRM,expired);signal.alarm(budget)
    result=dict(source_commit=commit,scope='Diagnostic only; no sampler change',boundaries=[],swaps=[],slices=[],resolution=[])
    def publish(status):save(root/'results.json',result);render(root,result);save(root/'status.json',dict(status=status))
    try:
        run_inputs.authenticate_files(dict(recipe=plan['recipe'],genesis=plan['genesis']))
        recipe=json.loads(Path(plan['recipe']['path']).read_text());require_original_coordinates(recipe)
        if recipe['model']!='flat':raise ValueError('Flat only')
        env=run_inputs.authenticate_environment(gpu_runtime=recipe['gpu_runtime']);result['environment_identity']=digest(env)
        geometry_audit=[]
        base,_,_,_=run_inputs.load_inputs(recipe['files'],recipe['factor_ids'],genesis_path=plan['genesis']['path'],dataset_recipe=recipe['dataset_recipe'],migration_geometry_audit=geometry_audit)
        target=FlatTarget(base.inputs,base.geometry,base.rule,factor_ids=base.factor_ids,range_prior=recipe['flat_range_prior'])
        result['geometry_audit']=geometry_audit
        full=jax.jit(target._kernels['value_grad'])
        def load(p):
            with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
        states=[];snapshots=[]
        for case in plan['cases']:
            run_inputs.authenticate_files({k:case[k] for k in ['report','index','conditional']})
            report=json.loads(Path(case['report']['path']).read_text());index=json.loads(Path(case['index']['path']).read_text())
            if not index['authenticated_transition_replay'] or report['policy'] is not None:raise ValueError('Authenticated original-coordinate replay required')
            if not all(x['comparison']['matches_recorded_transition'] for x in report['replays']):raise ValueError('Unverified replay')
            state=load(case['conditional']['path']);states.append(state)
            for row in index['rows']:
                p=Path(case['index']['path']).parent/row['file']
                if p.resolve().parent!=Path(case['index']['path']).parent.resolve():raise ValueError('Invalid snapshot path')
                if hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('Changed snapshot')
                snap=load(p)
                if any(logical_hash(snap[k])!=v for k,v in row['array_hashes'].items()):raise ValueError('Snapshot array mismatch')
                if row['context']['target_sha256']!=hashlib.sha256(target.identity.encode()).hexdigest():raise ValueError('Target mismatch')
                snapshots.append((case['name']+'/'+p.stem,snap))
        if len(states)!=2:raise ValueError('Exactly two authenticated states required')
        early,late=states
        if not np.array_equal(early['inverse_mass'],late['inverse_mass']) or float(early['step'])!=float(late['step']):raise ValueError('Matched probes require identical inherited tuning')
        mass=early['inverse_mass'];step=float(early['step']);momenta=[s['momentum'] for s in states]
        def bind(s):
            u,ct,p=(jnp.asarray(s[k]) for k in ['u','ct','penalty'])
            return lambda q:full(jnp.asarray(q),u,ct,p)
        result['coordinates']=['log_alpha','logit_zeta','log_ell_eta'];result['inverse_mass']=mass.tolist();result['step']=step
        publish('authenticated')
        for name,s in snapshots:
            vg=bind(s);q=s['position']
            row=dict(name=name,curvature=[curvature(vg,q,mass,step,e) for e in [1e-4,3e-5]],
                     native=probe(vg,q,momenta[0],mass,step,plan['probe_steps']),
                     common_start=probe(vg,early['position'],momenta[0],mass,step,plan['probe_steps']))
            result['boundaries'].append(row)
        publish('boundaries_complete');print('BOUNDARIES_COMPLETE',len(snapshots),flush=True)
        keys=['position','u','ct','penalty']
        arms=[tuple(k for k,on in zip(keys,bits) if on) for bits in itertools.product([False,True],repeat=4)]
        arms.append(('alpha_only',))
        for keys in arms:
            s=swapped(early,late,keys);vg=bind(s);paths=[]
            for p in momenta:
                for sign in [1,-1]:paths.append(probe(vg,s['position'],p,mass,sign*step,plan['probe_steps']))
            name='+'.join(keys) or 'early_baseline'
            result['swaps'].append(dict(name=name,paths=paths))
            publish('swap_complete');print('SWAP_COMPLETE',name,max(p['max_abs_energy_error'] for p in paths),flush=True)
        for name,s in [('early',early),('late',late)]:
            vg=bind(s)
            for pindex,p in enumerate(momenta):
                for sign in [1,-1]:
                    result['resolution'].append(dict(name=name,momentum_index=pindex,direction=sign,path=probe(vg,s['position'],p,mass,sign*step/4,4*plan['probe_steps'])))
            for axis,label in [(0,'log amplitude'),(1,'logit spatial fraction')]:
                n=plan['slice_points'];width=np.array(plan['slice_halfwidths']);q=s['position']
                xs=np.linspace(q[axis]-width[axis],q[axis]+width[axis],n);ys=np.linspace(q[2]-width[2],q[2]+width[2],n);values=[]
                for y in ys:
                    line=[]
                    for x in xs:
                        qp=q.copy();qp[axis]=x;qp[2]=y;line.append(float(vg(qp)[0]))
                    values.append(line)
                a=np.array(values);a-=np.max(a[np.isfinite(a)])
                result['slices'].append(dict(name=name+' / '+label,x_name=label,x=xs.tolist(),y=ys.tolist(),relative_logdensity=a.tolist()))
            publish('slices_complete')
        publish('complete')
    except Exception as exc:
        result['error']=dict(type=type(exc).__name__,message=str(exc));publish('stopped');raise
    finally:signal.alarm(0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--commit',required=True)
    args=parser.parse_args();run(args.plan,args.commit)
