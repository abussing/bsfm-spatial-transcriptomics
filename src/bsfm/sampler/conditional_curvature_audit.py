"""Read-only local geometry of authenticated captured field conditionals.

Lanczos uses finite differences of the implemented analytic gradient. Its Ritz
values are estimates, not global stability guarantees. No sampler is advanced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import jax
import jax.numpy as jnp
from . import run_inputs
from .run import check_repository
from .layer4 import CenteredHyperTarget


def lanczos_extremes(product, dimension, steps=24, seed=817):
    """Symmetric Ritz approximation with full reorthogonalization."""
    rng=np.random.default_rng(seed)
    v=rng.normal(size=dimension);v/=np.linalg.norm(v)
    basis=[];images=[]
    for _ in range(min(steps,dimension)):
        basis.append(v.copy());w=np.asarray(product(v));images.append(w.copy())
        Q=np.column_stack(basis)
        for _ in range(2):w-=Q@(Q.T@w)
        norm=np.linalg.norm(w)
        if norm<1e-11:break
        v=w/norm
    Q=np.column_stack(basis);AQ=np.column_stack(images)
    small=Q.T@AQ;asym=np.linalg.norm(small-small.T)
    eig,V=np.linalg.eigh((small+small.T)/2)
    top=Q@V[:,-1]
    residual=np.linalg.norm(AQ@V[:,-1]-eig[-1]*top)
    return dict(minimum=float(eig[0]),maximum=float(eig[-1]),residual=float(residual),
                projected_asymmetry=float(asym),iterations=len(basis)),top


def run(path,commit):
    check_repository(path,commit);plan=json.loads(Path(path).read_text())
    if plan['source_commit']!=commit:raise ValueError('Commit mismatch')
    run_inputs.authenticate_files(plan['files'])
    recipe=json.loads(Path(plan['files']['recipe']['path']).read_text())
    run_inputs.authenticate_environment(gpu_runtime=recipe['gpu_runtime'])
    target,_,_,_=run_inputs.load_inputs(recipe['files'],recipe['factor_ids'],
        genesis_path=plan['files']['genesis']['path'],dataset_recipe=recipe['dataset_recipe'])
    maps=CenteredHyperTarget(target)._kernels
    indices=np.r_[0,1,np.arange(4,target.position_dimension)]
    captured=[]
    for name in ['early','late']:
        with np.load(plan['files'][name]['path'],allow_pickle=False) as f:
            captured.append({k:np.array(f[k]) for k in f.files})
    output=Path(plan['output']).resolve()
    if output.is_relative_to(run_inputs.REPO.resolve()) or output.exists():raise ValueError('Fresh external output required')
    output.mkdir(parents=True)
    results=[]
    # Counterfactual isolates the whitening geometry, holding physical W and
    # all current likelihood statistics fixed. It is not a posterior draw.
    variants=[('early',captured[0],None),('late',captured[1],None),
              ('late_with_early_whitening',captured[1],captured[0]['position'][2:4])]
    for name,c,xb in variants:
        q=jnp.asarray(c['position']);invariant=0.
        if xb is not None:
            W=maps['physical'](q[2:4],q[4:].reshape(-1,2))
            z=maps['whiten'](jnp.asarray(xb),W)
            q=q.at[2:4].set(xb).at[4:].set(z.reshape(-1))
            invariant=float(jnp.linalg.norm(maps['physical'](q[2:4],z)-W)/jnp.linalg.norm(W))
            if invariant>2e-8:raise ValueError('Counterfactual changed physical W')
        args=tuple(jnp.asarray(c[k]) for k in ['u','ct','penalty'])
        vg=jax.jit(lambda x: (lambda v,g:(v,g[indices]))(*target._kernels['value_grad'](q.at[indices].set(x),*args)))
        x=q[indices];sqrtmass=np.sqrt(c['inverse_mass'][indices]);h=float(c['step'])
        result=dict(name=name,physical_W_relative_error=invariant,step=h,spectra=[])
        for eps in [3e-4,1e-4]:
            def product(v):
                delta=jnp.asarray(eps*sqrtmass*v)
                return -sqrtmass*(np.asarray(vg(x+delta)[1])-np.asarray(vg(x-delta)[1]))/(2*eps)
            spectrum,vec=lanczos_extremes(product,len(indices),steps=plan['lanczos_steps'])
            spectrum.update(epsilon=eps,local_step_number=h*np.sqrt(max(0,spectrum['maximum'])),scalar_share=float(np.sum(vec[:2]**2)))
            direction=jnp.asarray(sqrtmass*vec);value,grad=vg(x)
            fd=float((vg(x+eps*direction)[0]-vg(x-eps*direction)[0])/(2*eps));exact=float(grad@direction)
            spectrum['directional_gradient_scaled_error']=abs(fd-exact)/max(1,abs(exact))
            result['spectra'].append(spectrum)
            print(name,json.dumps(spectrum),flush=True)
        results.append(result)
        (output/'report.json').write_text(json.dumps(dict(source_commit=commit,plan_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),results=results),indent=2)+'\n')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--plan',required=True);parser.add_argument('--commit',required=True)
    args=parser.parse_args();run(args.plan,args.commit)
