"""Read saved genesis; isolate first factor without warmup, saving or full fits."""
import argparse,copy,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo/'src'),str(repo/'docs/holdouts/s10-grid-20261103')]
import numpy as np
import jax
from experiment import clean,target_and_seeds
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_genesis import load_genesis
from bsfm.sampler.run_storage import read_json,file_record
from bsfm.sampler.layer5 import SplitTransition
from bsfm.sampler.contracts import logical_hash

clean(a.commit);a.output.mkdir(parents=True,exist_ok=False)
receipt=dict(status='INCOMPLETE',commit=a.commit,scope='First-factor reproducibility isolation; no warmup or output migration',environment=authenticate_gpu_environment())
source=Path('/work/abussing/bsfm-consolidation/evidence/real-timing-22015787/threads-1/strict')
genesis=source/'segments/segment/genesis/endpoint.npz'
prepared=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/circles12_diameter1of8/prepared')
class Captured(Exception):pass
def compare(x,y):
    result=[]
    for i,(u,v) in enumerate(zip(jax.tree.leaves(x),jax.tree.leaves(y))):
        u=np.asarray(u);v=np.asarray(v)
        if not np.array_equal(u,v):
            row=dict(leaf=i,shape=list(u.shape),dtype=str(u.dtype))
            if np.issubdtype(u.dtype,np.number):row['max_abs']=float(np.max(np.abs(u-v)))
            result.append(row)
    return dict(exact=not result,differences=result)
try:
    target,loading,eta,_=target_and_seeds(prepared,'deep',genesis)
    spec=read_json(source/'run-spec.json');binding=read_json(source/'input-receipt.json')
    # Original software contract authenticates the saved input only. This probe's
    # generating code identity is separately recorded; no old-contract state saved.
    c=RunController(a.output/'unused',target,loading,eta,spec,binding,authenticate=target._validate_identities)
    e,_=load_genesis(genesis,target,c.cp)
    receipt['genesis']=dict(path=str(genesis),**file_record(genesis))
    original=c.layer.split.transition
    def probe(key,position,state,tuning,*,state_factor_ids,prepared_context):
        receipt['factor']=position.factor_id
        receipt['input_context']=json.loads(prepared_context.context_json)
        receipt['input_position_sha256']=logical_hash(position.values)
        receipt['key']=np.asarray(jax.random.key_data(key)).tolist()
        np.savez_compressed(a.output/'first-factor-input.npz',position=position.values,u=prepared_context.u,
            ct=prepared_context.ct,penalty=prepared_context.penalty,mass=tuning.inverse_mass_matrix,
            field_step=tuning.step_size,hyper_step=tuning.hyper_step_size,key=np.asarray(jax.random.key_data(key)))
        runs=[]
        for label in ['same_runner_first','same_runner_repeat','new_runner']:
            start=time.monotonic()
            if label=='new_runner':
                result=SplitTransition(target).transition(key,position,state,tuning,state_factor_ids=state_factor_ids)
            else:
                result=original(key,position,state,tuning,state_factor_ids=state_factor_ids,prepared_context=prepared_context)
            receipt[label]=dict(seconds=time.monotonic()-start,position_sha256=logical_hash(result.position.values),audit=result.audit)
            runs.append(result)
            print('PROBE',label,receipt[label]['seconds'],flush=True)
        receipt['same_runner_repeat']=dict(receipt['same_runner_repeat'],comparison=compare((runs[0].nuts_state,runs[0].info),(runs[1].nuts_state,runs[1].info)))
        receipt['new_runner']['comparison']=compare((runs[0].nuts_state,runs[0].info),(runs[2].nuts_state,runs[2].info))
        fid=target.factor_ids.index(position.factor_id)
        for arm in ['strict','incremental']:
            path=source.parent/arm/'segments/segment/transactions/000000000001/checkpoint.npz'
            with np.load(path,allow_pickle=False) as z:
                receipt['against_saved_'+arm]=compare(runs[0].position.values,z['positions'][fid])
        raise Captured()
    c.layer.split.transition=probe
    work=copy.deepcopy(e);np.random.set_state(work.numpy_global_state)
    try:
        c.layer.sweep(work.state,work.positions,work.tuning,eta_rng=work.eta_rng,gauge_rng=work.gauge_rng,
            master_key=work.master_key,state_factor_ids=target.factor_ids,label='diagnostic-first-factor')
    except Captured:pass
    else:raise AssertionError('Probe not reached')
    receipt['status']='DIAGNOSTIC_COMPLETE'
except BaseException as exc:
    receipt.update(status='FAIL',error=repr(exc));raise
finally:
    (a.output/'diagnostic.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('DIAGNOSTIC',receipt['status'],flush=True)
