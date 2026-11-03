"""Proposed synthetic GPU/GPFS gate. No scientific inputs or live run roots."""
import argparse,copy,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--commit',required=True)
p.add_argument('--worker',action='store_true');a=p.parse_args()
repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo/'src'),str(repo/'tests'),str(repo/'docs/holdouts/s10-grid-20261103')]
if subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()!=a.commit:
    raise ValueError('Wrong validation commit')
if subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():
    raise ValueError('Dirty validation checkout')
import jax
import jax.numpy as jnp
import numpy as np
from gpu_run import authenticate_gpu_environment
from sampler_layer9_support import controller
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_incremental import IncrementalTransactions
from bsfm.sampler.run_storage import read_json,file_record
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.split_kernels import gpu_acceptance_roundoff
runtime=authenticate_gpu_environment()
probe=jax.jit(gpu_acceptance_roundoff)(jnp.array([1+np.finfo(np.float64).eps]))
probe.block_until_ready();jax.effects_barrier()
assert probe.device.platform=='gpu' and float(probe[0])==1

def make(root,incremental):
    c=controller(root,final=3)
    spec=copy.deepcopy(c.spec)
    spec['software'].update(git_commit=a.commit,clean_tree=True,
        environment_identity=digest(runtime),environment_lock_sha256=runtime['lock']['sha256'])
    spec['software']['run_config_sha256']=digest({'scope':'synthetic strict/incremental comparison',
        'seed':spec['seed'],'warmup':20,'sweeps':3,'target':c.target.identity})
    result=RunController(root,c.target,c.loading,c.eta,spec,c.store.input_receipt,
                         authenticate=c.target._validate_identities)
    result.layer=c.layer
    if incremental:
        result.store=IncrementalTransactions(root,result.target,result.cp,result.rc,result.scale,spec,c.store.input_receipt)
    return result

if a.worker:
    def die(stage):
        if stage=='after_sweep':os._exit(91)
    make(a.output,True).run(stop_after=2,fault=die)
    raise AssertionError('Expected interruption was not reached')

a.output.mkdir(parents=True,exist_ok=False)
receipt={'commit':a.commit,'environment':runtime,'scope':'Synthetic GPU/GPFS only; no scientific fit',
         'status':'INCOMPLETE','checks':[],'timing':{}}
def compare(left,right,label):
    for n in (1,2,3):
        rel=Path('segments/segment/transactions')/f'{n:012d}'
        assert read_json(left/rel/'prepared.json')==read_json(right/rel/'prepared.json')
    receipt['checks'].append({'case':label,'all_three_transaction_receipts_exact':True})
try:
    for label,mode in [('strict',False),('incremental',True)]:
        start=time.monotonic();events=[];sweep=[0]
        def event(stage):
            if stage=='before_sweep':sweep[0]+=1
            events.append({'stage':stage,'sweep':sweep[0],'seconds_since_start':time.monotonic()-start})
        c=make(a.output/label,mode);result=c.run(fault=event)
        receipt['timing'][label]={'total_seconds_including_compilation_warmup_validation':time.monotonic()-start,
            'phase_events':events,
            'sweep_seconds':[read_json(q)['elapsed_seconds'] for q in sorted((c.store.segment/'attempts').glob('sweep-*/performance.json'))],
            'timing_limit':'Phase events measure host wall time; compilation and cache order differ between arms. Not a matched throughput benchmark.'}
        receipt[label+'_completion']=result
    compare(a.output/'strict',a.output/'incremental','strict versus incremental')
    # Fresh root contains copied validated genesis and exactly one committed
    # transaction, never a forged numerical boundary or duplicated chain row.
    source=a.output/'incremental';restart=a.output/'restart';restart.mkdir()
    for name in ['run-spec.json','input-receipt.json']:shutil.copyfile(source/name,restart/name)
    seg=restart/'segments/segment';seg.mkdir(parents=True)
    shutil.copytree(source/'segments/segment/genesis',seg/'genesis')
    (seg/'transactions').mkdir()
    shutil.copytree(source/'segments/segment/transactions/000000000001',seg/'transactions/000000000001')
    worker=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--output',str(restart),'--commit',a.commit,'--worker'])
    assert worker.returncode==91
    make(restart,True).run()
    compare(source,restart,'fresh-process uncommitted sweep recomputation')
    done=make(restart,True)
    def no_sweep(*args,**kwargs):raise AssertionError('Committed sweep replay')
    done.layer.sweep=no_sweep
    done.run();receipt['checks'].append({'case':'completed non-replay','pass':True})
    receipt['outputs']={str(q.relative_to(a.output)):file_record(q)
        for q in a.output.glob('*/segments/segment/transactions/*/prepared.json')}
    receipt['status']='PASS'
except BaseException as exc:
    receipt['status']='FAIL';receipt['error']=repr(exc);raise
finally:
    (a.output/'validation.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('GPU_WORKFLOW_VALIDATION',receipt['status'],flush=True)
