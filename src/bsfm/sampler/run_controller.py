"""Bounded CPU run composition. No readaptation or scientific defaults."""
from pathlib import Path
import copy
import re
import tempfile
import time
import numpy as np
from .checkpoint import save_checkpoint_atomic
from .checkpoint_contract import build_checkpoint_contract, digest
from .checkpoint_rng import exact_keys
from .retained_contract import build_retained_contract
from .retained_records import make_completed
from .retained_archive import aggregate_archives
from .retained_diagnostics import decode
from .layer6 import GibbsSweep
from .run_initialization import initialize, adapt
from .run_genesis import save_genesis, load_genesis
from .run_storage import writer, read_json, write_json, write_npz, publish, file_record
from .run_transactions import Transactions
from .run_receipts import publish_json


def validate_spec(spec):
    exact_keys(spec,('schema','run_id','segment_id','chain_id','factor_ids','seed','warmup_steps',
        'settling_sweeps','production_sweeps','save_every','checkpoint_every','final_sweep',
        'mode','input_sha256','software'))
    if spec['schema']!='bsfm.local-run.v1' or spec['mode']!='exact_resume':raise ValueError('Only exact same-run resume supported; readaptation deferred')
    for n in ('run_id','segment_id','chain_id'):
        if not isinstance(spec[n],str) or not re.fullmatch('[A-Za-z0-9_-]+',spec[n]):raise ValueError('Explicit safe run/segment/chain identity required')
    for n,minimum in [('seed',0),('warmup_steps',20),('settling_sweeps',0),('production_sweeps',1),('save_every',1),('checkpoint_every',1),('final_sweep',1)]:
        if type(spec[n]) is not int or spec[n]<minimum:raise ValueError('Invalid explicit run count: '+n)
    if spec['final_sweep']!=spec['settling_sweeps']+spec['production_sweeps']:raise ValueError('Run-length mismatch')
    return spec


class RunController:
    """Authenticate callback runs before work and closure; synthetic tests attest fixtures.

    Real inputs use run_inputs.canonical_controller, including clean Git/environment
    authentication. The lower-level API supports explicit synthetic fixtures only
    when their software contract honestly records the dirty review tree.
    """
    def __init__(self,root,target,loading,eta,spec,input_receipt,*,authenticate):
        self.spec=validate_spec(spec);self.target=target;self.loading=loading;self.eta=eta
        if spec['factor_ids']!=list(target.factor_ids) or spec['input_sha256']!=digest(input_receipt):raise ValueError('Run inputs/factors mismatch')
        self.authenticate=authenticate
        self.scale=.25*np.var(target.inputs.arrays['Y'],axis=1)
        sw=spec['software'];self.cp=build_checkpoint_contract(target,b_sigma2=self.scale,software=sw,expected_software_sha256=digest(sw))
        self.rc=build_retained_contract(target,b_sigma2=self.scale,software=sw,expected_software_sha256=digest(sw),chain_id=spec['chain_id'],
            save_every=spec['save_every'],settling_sweeps=spec['settling_sweeps'],final_sweep=spec['final_sweep'])
        self.store=Transactions(root,target,self.cp,self.rc,self.scale,spec,input_receipt)
        self.layer=GibbsSweep(target,b_sigma2=self.scale)

    def _genesis(self,fault):
        s=self.store;final=s.segment/'genesis'
        def read(path):
            if sorted(p.name for p in path.iterdir())!=['endpoint.npz','receipt.json']:raise ValueError('Incomplete genesis envelope')
            e,h=load_genesis(path/'endpoint.npz',self.target,self.cp)
            if (e.evidence['adaptation_steps']!=self.spec['warmup_steps']
                    or e.evidence['initialization']['seed']!=self.spec['seed']):
                raise ValueError('Genesis initialization/warmup differs from run specification')
            expected=dict(schema='bsfm.genesis.v1',spec_sha256=s.spec_hash,input_sha256=self.spec['input_sha256'],
                endpoint=file_record(path/'endpoint.npz'),logical_sha256=h)
            if read_json(path/'receipt.json')!=expected:raise ValueError('Genesis receipt mismatch')
            return e,digest(expected)
        if final.exists():return read(final)
        complete=[p/'genesis' for p in (s.segment/'attempts').iterdir() if (p/'genesis/receipt.json').exists()]
        if len(complete)>1:raise ValueError('Multiple prepared genesis candidates')
        if complete:
            value=read(complete[0]);publish(complete[0],final);return value
        attempt=Path(tempfile.mkdtemp(prefix='genesis-',dir=s.segment/'attempts'));path=attempt/'genesis';path.mkdir()
        fault('before_initialization');start=time.perf_counter()
        try:
            e,keys=initialize(self.target,self.loading,self.eta,seed=self.spec['seed'])
            fault('after_initialization')
            e=adapt(self.target,e,keys,steps=self.spec['warmup_steps'],split=self.layer.split)
        except (ValueError,RuntimeError,FloatingPointError) as exc:
            write_json(s.segment/'failures'/('initialization-'+attempt.name+'.json'),dict(stage='initialization_warmup',error=str(exc)));raise
        write_json(attempt/'performance.json',dict(elapsed_seconds=time.perf_counter()-start,scope='initialization_and_warmup'))
        fault('after_warmup');_,h=save_genesis(path/'endpoint.npz',e,self.target,self.cp)
        publish_json(path/'receipt.json',dict(schema='bsfm.genesis.v1',spec_sha256=s.spec_hash,input_sha256=self.spec['input_sha256'],endpoint=file_record(path/'endpoint.npz'),logical_sha256=h),staging_directory=attempt)
        value=read(path);fault('before_genesis_publish');publish(path,final);fault('after_genesis_publish');return value

    def run(self,*,stop_after=None,fault=lambda stage:None):
        if stop_after is not None and (type(stop_after) is not int or stop_after<0):raise ValueError('Invalid pause boundary')
        s=self.store
        validate_spec(self.spec)
        if digest(self.spec)!=s.spec_hash or digest(s.input_receipt)!=self.spec['input_sha256']:
            raise ValueError('In-memory run/input identity changed')
        with writer(s.root):
            self.authenticate();s.setup();genesis,gid=self._genesis(fault)
            while True:
                chain=s.scan(genesis,gid);n=len(chain['rows'])
                if n>self.spec['final_sweep']:raise ValueError('Extra committed sweep')
                if n<self.spec['final_sweep'] and s.recover_prepared(chain,fault):continue
                archive=s.repair(chain,fault)
                if n==self.spec['final_sweep']:
                    self.authenticate();aggregate=aggregate_archives([archive])
                    warm=sum(int(np.asarray(decode(r['history'])['info']['block_divergent']).sum()) for r in genesis.evidence['factors'])
                    sweep_div=sum(aggregate['chains'][self.spec['chain_id']]['divergence_counts'])
                    closure=dict(schema='bsfm.run-completion.v1',status='complete_with_warnings' if warm+sweep_div else 'complete',
                        head=chain['head'],spec_sha256=s.spec_hash,completed=n,retained=chain['retained'],
                        warmup_divergences=warm,aggregate=aggregate,convergence_status='not_assessed')
                    dest=s.segment/'completion.json'
                    if dest.exists():
                        if read_json(dest)!=closure:raise ValueError('Completion mismatch')
                    else:
                        p=Path(tempfile.mkdtemp(prefix='closure-',dir=s.segment/'attempts'))/'completion.json'
                        write_json(p,closure);fault('before_completion');publish(p,dest)
                    if read_json(dest)!=closure:raise ValueError('Completion readback mismatch')
                    return closure
                if (s.segment/'completion.json').exists():raise ValueError('Premature completion')
                if stop_after is not None and n>=stop_after:return dict(status='paused',completed=n,head=chain['head'])
                # The sweep owns advancing RNGs; genesis remains a durable-boundary
                # reference for subsequent scans and must not share those streams.
                e=copy.deepcopy(chain['endpoint']);np.random.set_state(e.numpy_global_state)
                attempt=Path(tempfile.mkdtemp(prefix=f'sweep-{n+1:012d}-',dir=s.segment/'attempts'))
                write_json(attempt/'intent.json',dict(sweep=n+1,previous_sha256=chain['head'],spec_sha256=s.spec_hash))
                path=attempt/'transaction';path.mkdir();fault('before_sweep');start=time.perf_counter()
                try:
                    result=self.layer.sweep(e.state,e.positions,e.tuning,eta_rng=e.eta_rng,gauge_rng=e.gauge_rng,
                        master_key=e.master_key,state_factor_ids=self.target.factor_ids,label=s.label(n+1))
                except (ValueError,RuntimeError,FloatingPointError) as exc:
                    write_json(s.segment/'failures'/(attempt.name+'.json'),dict(stage='sweep',sweep=n+1,head=chain['head'],error=str(exc)));raise
                fault('after_sweep');write_json(attempt/'performance.json',dict(elapsed_seconds=time.perf_counter()-start,scope='sweep_only'))
                progress=dict(completed_local_sweep=n+1,settling_sweeps=self.spec['settling_sweeps'],completed_production_sweeps=max(0,n+1-self.spec['settling_sweeps']),checkpoint_type='complete',status='completed_sweep')
                save_checkpoint_atomic(path/'checkpoint.npz',target=self.target,contract=self.cp,result=result,tuning=e.tuning,eta_rng=e.eta_rng,gauge_rng=e.gauge_rng,b_sigma2=self.scale,progress=progress)
                fault('after_checkpoint_candidate')
                data=make_completed(self.target,self.rc,self.scale,result,sweep=n+1,retained_index=chain['retained']+1,previous_sha256=chain['record_head'],events=[],elapsed_seconds=None)
                write_npz(path/'record.npz',data);fault('after_record_candidate')
                # Normal path and recovery use the same independent pair validator.
                s.recover_prepared(chain,fault)
