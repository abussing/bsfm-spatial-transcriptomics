"""Real GPU periodic/restart gate from saved seed; CPU held-out scoring check."""
import argparse,copy,json,os,shutil,subprocess,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
p.add_argument('--worker',choices=['run','interrupt','resume','nonreplay']);a=p.parse_args()
repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo/'src'),str(repo/'docs/holdouts/s10-grid-20261103')]
import numpy as np
from experiment import clean,target_and_seeds
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_periodic import PeriodicRunController
from bsfm.sampler.run_genesis import load_genesis
from bsfm.sampler.compact_checkpoint import load_compact
from bsfm.sampler.checkpoint import load_checkpoint
from bsfm.sampler.run_storage import read_json,file_record
from bsfm.sampler.checkpoint_contract import digest
source=Path('/work/abussing/bsfm-consolidation/evidence/real-timing-22015787/threads-1/strict')
reference=Path('/work/abussing/bsfm-consolidation/evidence/real-replay-22015934/strict')
genesis=source/'segments/segment/genesis/endpoint.npz'
prepared=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/circles12_diameter1of8/prepared')

def make(root):
    clean(a.commit);runtime=authenticate_gpu_environment()
    target,loading,eta,_=target_and_seeds(prepared,'deep',genesis)
    oldspec=read_json(source/'run-spec.json');binding=read_json(source/'input-receipt.json')
    old=RunController(root/'unused',target,loading,eta,oldspec,binding,authenticate=target._validate_identities)
    seed,_=load_genesis(genesis,target,old.cp)
    spec=read_json(reference/'run-spec.json');spec.update(save_every=3,checkpoint_every=3)
    spec['software']=dict(git_commit=a.commit,clean_tree=True,environment_identity=digest(runtime),
        environment_lock_sha256=runtime['lock']['sha256'],
        run_config_sha256=digest(dict(scope='periodic diagnostic seed',source=file_record(genesis),cadence=3,sweeps=3)))
    c=PeriodicRunController(root,target,loading,eta,spec,binding,authenticate=target._validate_identities)
    c._adapt_endpoint=lambda fault:copy.deepcopy(seed)
    return c

if a.worker:
    root=a.output/('run' if a.worker=='run' else 'restart')/'deep/production'
    c=make(root)
    def fault(stage):
        if a.worker=='interrupt' and stage=='after_sweep':os._exit(91)
    if a.worker=='nonreplay':
        def fail(*args,**kw):raise AssertionError('Committed sweep replay')
        c.layer.sweep=fail
    result=c.run(fault=fault)
    (a.output/(a.worker+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    sys.exit(0)

a.output.mkdir(parents=True,exist_ok=False)
r=dict(status='INCOMPLETE',commit=a.commit,scope='Three real-size diagnostic sweeps, sparse saving, restart and actual held-out scoring; no warmup',checks=[])
def worker(name,expected=0):
    result=subprocess.run([sys.executable,'-u',str(Path(__file__).resolve()),'--commit',a.commit,'--output',str(a.output),'--worker',name])
    if result.returncode!=expected:raise AssertionError((name,result.returncode))
try:
    worker('run')
    c=make(a.output/'run/deep/production')
    oldspec=read_json(reference/'run-spec.json');old=RunController(a.output/'old-unused',c.target,c.loading,c.eta,oldspec,c.store.input_receipt,authenticate=c.target._validate_identities)
    sizes={}
    for n in (1,3):
        path=c.store.segment/'boundaries'/f'{n:012d}'
        new=load_compact(path/'checkpoint.npz',target=c.target,contract=c.cp)
        previous=load_checkpoint(reference/'segments/segment/transactions'/f'{n:012d}'/'checkpoint.npz',target=c.target,contract=old.cp)
        assert new.boundary==previous.boundary,'Changed numerical/RNG endpoint'
        sizes[str(n)]={p.name:p.stat().st_size for p in path.iterdir()}
    assert sorted(p.name for p in (c.store.segment/'boundaries').iterdir())==['000000000001','000000000003']
    r['checks'].append('Periodic sweeps 1 and 3 match previous every-sweep GPU state/RNG exactly')
    restart=a.output/'restart/deep/production';restart.mkdir(parents=True)
    for name in ['run-spec.json','input-receipt.json']:shutil.copyfile(c.store.root/name,restart/name)
    seg=restart/'segments/segment';seg.mkdir(parents=True)
    shutil.copytree(c.store.segment/'genesis',seg/'genesis');(seg/'boundaries').mkdir()
    shutil.copytree(c.store.segment/'boundaries/000000000001',seg/'boundaries/000000000001')
    worker('interrupt',91);worker('resume')
    for n in (1,3):
        rel=Path('segments/segment/boundaries')/f'{n:012d}'/'receipt.json'
        assert read_json(c.store.root/rel)==read_json(restart/rel)
    worker('nonreplay');r['checks'].append('Fresh-process unsaved sweep recomputed exactly; completed boundaries never replayed')
    env=dict(os.environ,JAX_PLATFORMS='cpu')
    command=[sys.executable,'-u',str(repo/'docs/holdouts/s10-grid-20261103/periodic_prediction.py'),str(prepared),str(a.output/'run'),'deep',a.commit]
    subprocess.run(command,env=env,check=True)
    prediction=a.output/'run/predictions/deep/latest.npz';before=file_record(prediction)
    subprocess.run(command,env=env,check=True);assert file_record(prediction)==before
    with np.load(prediction,allow_pickle=False) as z:
        meta=json.loads(str(z['metadata']));assert meta['prediction_draws']==2
        assert np.isfinite(z['pointwise_log_predictive_density']).all()
        assert np.isfinite(z['mean']).all() and np.all(z['variance']>0)
    r.update(status='PASS',bytes_per_boundary=sizes,prediction=dict(file=before,metadata=meta))
    r['checks'].append('Actual held-out predictive log densities finite; scorer restart does not double-count')
except BaseException as exc:
    r.update(status='FAIL',error=repr(exc));raise
finally:
    (a.output/'validation.json').write_text(json.dumps(r,indent=2)+'\n')
    print('PERIODIC_GATE',r['status'],flush=True)
