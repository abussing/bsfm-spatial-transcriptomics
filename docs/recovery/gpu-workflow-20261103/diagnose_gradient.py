"""Isolate repeated gradient/scatter execution on the captured first-factor input."""
import argparse,json,sys
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[3];sys.path[:0]=[str(repo/'src'),str(repo/'docs/holdouts/s10-grid-20261103')]
import numpy as np
import jax
import jax.numpy as jnp
from experiment import clean,target_and_seeds
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.field_target import kernel_arguments
from bsfm.sampler.finite_features import make_feature_kernel
clean(a.commit);a.output.mkdir(parents=True,exist_ok=False)
receipt=dict(status='INCOMPLETE',commit=a.commit,environment=authenticate_gpu_environment(),scope='Fixed-input gradient/scatter diagnostic; no transition, fit or production changes')
try:
    source=Path('/work/abussing/bsfm-consolidation/evidence/first-factor-22015888/first-factor-input.npz')
    genesis=Path('/work/abussing/bsfm-consolidation/evidence/real-timing-22015787/threads-1/strict/segments/segment/genesis/endpoint.npz')
    prepared=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/circles12_diameter1of8/prepared')
    target,_,_,_=target_and_seeds(prepared,'deep',genesis)
    with np.load(source,allow_pickle=False) as z:d={k:z[k].copy() for k in z.files}
    def repeat(fn,args):
        results=[]
        for _ in range(10):results.append(jax.tree.map(lambda x:np.asarray(x).copy(),fn(*args)))
        first=jax.tree.leaves(results[0]);diff=[]
        for r in results[1:]:
            leaves=jax.tree.leaves(r)
            diff.append(dict(exact=all(np.array_equal(x,y) for x,y in zip(first,leaves)),
                max_abs=max(float(np.max(np.abs(x-y))) for x,y in zip(first,leaves))))
        return dict(repeats=10,comparisons=diff,all_exact=all(x['exact'] for x in diff)),results[0]
    args=tuple(jnp.asarray(d[k]) for k in ['position','u','ct','penalty'])
    receipt['full_value_gradient'],_=repeat(jax.jit(target._kernels['value_grad']),args)
    ka=kernel_arguments(target.inputs,target.geometry,target.rule)
    idx=np.asarray(ka['cell_vertex_idx']);weights=jnp.asarray(ka['cell_weights']);n=ka['u_active'].shape[0]
    w=target._kernels['warp_features'](args[0])[0]
    _,parts,_=make_feature_kernel(ka['omega'],ka['sqrt_weights'])
    gradient=parts(w,args[0][0],args[0][1],jnp.log(.14),args[1],args[2])[1]
    contribution=(weights[:,:,None]*gradient[:,None,:]).reshape(-1,2)
    indices=jnp.asarray(idx.reshape(-1))
    def scatter(x):return jnp.zeros((n,2),jnp.float64).at[indices].add(x)
    groups=[np.flatnonzero(idx.reshape(-1)==i) for i in range(n)]
    width=max(map(len,groups));padded=np.zeros((n,width),np.int32);mask=np.zeros((n,width),bool)
    for i,g in enumerate(groups):padded[i,:len(g)]=g;mask[i,:len(g)]=True
    padded=jnp.asarray(padded);mask=jnp.asarray(mask)
    def fixed_order(x):return jnp.sum(jnp.where(mask[:,:,None],x[padded],0.),axis=1)
    receipt['scatter_add'],old=repeat(jax.jit(scatter),(contribution,))
    receipt['fixed_order_diagnostic_only'],new=repeat(jax.jit(fixed_order),(contribution,))
    reference=np.zeros((n,2));np.add.at(reference,idx.reshape(-1),np.asarray(contribution))
    receipt['operator_comparison']=dict(active_vertices=int(n),contributions=int(idx.size),max_incidence=int(width),
        scatter_vs_cpu_max_abs=float(np.max(np.abs(old-reference))),
        fixed_order_vs_cpu_max_abs=float(np.max(np.abs(new-reference))),
        scatter_vs_fixed_order_max_abs=float(np.max(np.abs(old-new))))
    receipt['status']='DIAGNOSTIC_COMPLETE'
except BaseException as exc:
    receipt.update(status='FAIL',error=repr(exc));raise
finally:
    (a.output/'diagnostic.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt),flush=True)
