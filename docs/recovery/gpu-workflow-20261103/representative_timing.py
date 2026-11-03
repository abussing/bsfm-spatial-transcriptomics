"""Isolated real-input timing; short tuning is mechanical, not scientific inference."""
import argparse,copy,json,shutil,sys,time
from functools import partial
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--threads',type=int,choices=[1,4],required=True);a=p.parse_args()
repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo/'src'),str(repo/'docs/holdouts/s10-grid-20261103')]
from experiment import controllers,use_incremental_store
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_storage import read_json
from bsfm.sampler.checkpoint_contract import digest

config='circles12_diameter1of8'
prepared=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea')/config/'prepared'
a.output.mkdir(parents=True,exist_ok=False)
auth=partial(authenticate_gpu_environment,blas_threads=a.threads)
receipt=dict(status='INCOMPLETE',commit=a.commit,threads=a.threads,configuration=config,model='deep',
    scope='K12 L14 real prepared hole subset; 20 tuning steps per factor and 3 sweeps; no scientific inference',arms={},
    limits='Strict executes first: compilation/cache order is not balanced. Compare post-sweep overhead separately. Three sweeps do not establish long-history scaling.')
try:
    base,binding,_=controllers(config,prepared,a.output/'unused', 'deep',a.commit,runtime_auth=auth)
    spec=copy.deepcopy(base.spec)
    spec.update(run_id='representative_timing',warmup_steps=20,production_sweeps=3,final_sweep=3)
    config_record={k:v for k,v in spec.items() if k!='software'}
    spec['software']['run_config_sha256']=digest(dict(configuration=config_record,scope='strict_incremental_timing',threads=a.threads))
    for label in ['strict','incremental']:
        root=a.output/label
        c=RunController(root,base.target,base.loading,base.eta,spec,binding,authenticate=base.authenticate)
        if label=='incremental':
            use_incremental_store(c)
            # Reuse exactly the authenticated adapted boundary, not repeated
            # adaptation with a potentially different numerical trajectory.
            dest=root/'segments/segment/genesis';dest.parent.mkdir(parents=True)
            shutil.copytree(a.output/'strict/segments/segment/genesis',dest)
        start=time.monotonic();events=[];sweep=[0]
        def event(stage):
            if stage=='before_sweep':sweep[0]+=1
            t=time.monotonic()-start
            events.append(dict(stage=stage,sweep=sweep[0],seconds=t))
            if stage in ['after_warmup','before_sweep','after_sweep','after_transaction_publish','before_completion']:
                print('TIMING',label,sweep[0],stage,round(t,3),flush=True)
        result=c.run(fault=event)
        receipt['arms'][label]=dict(total_seconds=time.monotonic()-start,events=events,completion=result)
        (a.output/'timing.json').write_text(json.dumps(receipt,indent=2)+'\n')
    for n in range(1,4):
        rel=Path('segments/segment/transactions')/f'{n:012d}'/'prepared.json'
        assert read_json(a.output/'strict'/rel)==read_json(a.output/'incremental'/rel)
    receipt.update(status='PASS',strict_incremental_transactions_exact=True,environment=auth())
except BaseException as exc:
    receipt.update(status='FAIL',error=repr(exc));raise
finally:
    (a.output/'timing.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('REPRESENTATIVE_TIMING',receipt['status'],flush=True)
