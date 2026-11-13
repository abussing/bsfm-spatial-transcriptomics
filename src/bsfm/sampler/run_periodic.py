"""Periodic atomic checkpoints/draws, with no per-sweep heavy serialization.

Unpublished sweeps are recomputed from the previous complete boundary. Published
boundaries are immutable; a receipt is published together with checkpoint, draw
and contiguous per-sweep diagnostics. No duplicate archive/checkpoint projections.
"""
import copy
from pathlib import Path
import tempfile
import time
import numpy as np
from .checkpoint_contract import digest
from .compact_checkpoint import load_compact, save_compact
from .retained_contract import retain_at
from .retained_records import make_completed, load_record, validate_audit
from .retained_diagnostics import encode, decode
from .run_controller import RunController, validate_spec
from .run_readaptation import ReadaptationController
from .run_genesis import boundary
from .run_initialization import Endpoint
from .run_storage import writer, read_json, write_json, write_npz, publish, file_record
from .run_transactions import tuning_identity


class PeriodicMixin:
    def _health(self,chain):
        if self.store.input_receipt.get('diagnostics')!='adaptation_study_v1':return None
        from .run_health import review_windows
        from .run_storage import advisory
        rows=[]
        for path in reversed(sorted((self.store.segment/'boundaries').iterdir())):
            if int(path.name)>chain['n']:continue
            rows=read_json(path/'diagnostics.json')+rows
            if len(rows)>=50:break
        from .flat_control import FlatTarget
        # Flat samples alpha/zeta/(optional range) jointly in the first block.
        # Its second slot is a compatibility placeholder, not a failed kernel.
        active_blocks=('field',) if isinstance(self.target,FlatTarget) else ('field','hyper')
        health=review_windows(rows,active_blocks=active_blocks)
        health.update(completed=chain['n'],head=chain['head'])
        advisory(self.store.root/'health.json',health)
        print('HEALTH',chain['n'],health['status'],flush=True)
        if health['status']=='review_required':return health

    def _due(self, n):
        return retain_at(self.store.records, n)

    def _start(self, genesis, gid):
        return dict(n=0, endpoint=genesis, boundary=boundary(genesis,self.target),
                    head=digest(dict(spec=self.store.spec_hash, genesis=gid)),
                    record_head=self.rc.sha256, retained=0,
                    tuning=tuning_identity(genesis.tuning))

    def _read_boundary(self, path, prior):
        if sorted(p.name for p in path.iterdir()) != ['checkpoint.npz','diagnostics.json','receipt.json','record.npz']:
            raise ValueError('Incomplete periodic boundary')
        receipt=read_json(path/'receipt.json')
        body={k:v for k,v in receipt.items() if k!='sha256'}
        if (receipt.get('sha256')!=digest(body) or receipt.get('schema')!='bsfm.periodic-boundary.v1'
                or receipt['previous']!=prior['head'] or receipt['spec_sha256']!=self.store.spec_hash):
            raise ValueError('Periodic receipt identity/chain mismatch')
        n=receipt['sweep']
        expected=next(i for i in range(prior['n']+1,self.spec['final_sweep']+1) if self._due(i))
        if n!=expected or path.name.isdigit() and path.name!=f'{n:012d}':
            raise ValueError('Gapped/unexpected periodic sweep')
        for name in ('checkpoint.npz','record.npz','diagnostics.json'):
            if file_record(path/name)!=receipt['files'][name]:
                raise ValueError('Periodic payload changed')
        rows=read_json(path/'diagnostics.json')
        cap=self.store.input_receipt.get('pcg_maximum_iterations',80)
        if any(p['iterations']>cap for row in rows for p in decode(row['pcg'])):
            raise ValueError('PCG diagnostics exceed frozen run iteration budget')
        if [r['sweep'] for r in rows]!=list(range(prior['n']+1,n+1)):
            raise ValueError('Missing periodic sweep diagnostics')
        b=prior['boundary']
        for row in rows:
            audit=row['audit'];validate_audit(audit,self.target,self.scale)
            for before,after in [('state_before','state_after'),('positions_before','positions_after'),('rng_before','rng_after')]:
                if audit[before]!=b[after]:raise ValueError('Periodic state/RNG discontinuity')
            if audit['label']!=self.store.label(row['sweep']):raise ValueError('Sweep label mismatch')
            b=audit
        e=load_compact(path/'checkpoint.npz',target=self.target,contract=self.cp)
        m,_,d=load_record(path/'record.npz',target=self.target,contract=self.rc,b_sigma2=self.scale)
        if (e.progress['completed_local_sweep']!=n or m['sweep']!=n
                or m['retained_index']!=prior['retained']+1 or m['previous_sha256']!=prior['record_head']
                or d['sweep_audit']!=b or any(b.get(k)!=v for k,v in e.boundary.items())
                or tuning_identity(e.tuning)!=prior['tuning']):
            raise ValueError('Periodic checkpoint/draw/diagnostic mismatch')
        return dict(n=n,endpoint=e,boundary=e.boundary,head=receipt['sha256'],
                    record_head=m['logical_sha256'],retained=prior['retained']+1,tuning=prior['tuning'])

    def _scan(self, genesis, gid):
        chain=self._start(genesis,gid)
        root=self.store.segment/'boundaries';root.mkdir(exist_ok=True)
        for path in sorted(root.iterdir()):
            if not path.name.isdigit() or len(path.name)!=12:raise ValueError('Unexpected periodic boundary path')
            chain=self._read_boundary(path,chain)
        return chain

    def _recover(self, chain):
        candidates=[]
        for p in (self.store.segment/'attempts').glob('periodic-*/boundary'):
            if not (p/'receipt.json').exists():continue
            r=read_json(p/'receipt.json')
            if r['sweep']<=chain['n']:continue
            candidate=self._read_boundary(p,chain)
            candidates.append((p,candidate))
        if len(candidates)>1:raise ValueError('Ambiguous periodic publication candidates')
        if candidates:
            p,chain=candidates[0]
            publish(p,self.store.segment/'boundaries'/f"{chain['n']:012d}")
        return chain

    def run(self, *, stop_after=None, fault=lambda stage:None):
        validate_spec(self.spec)
        if self.spec['settling_sweeps']!=0 or self.spec['save_every']!=self.spec['checkpoint_every']:
            raise ValueError('Periodic v1 requires zero settling and matched checkpoint/draw cadence')
        if digest(self.spec)!=self.store.spec_hash or digest(self.store.input_receipt)!=self.spec['input_sha256']:
            raise ValueError('Run spec/input changed')
        if stop_after is not None and (type(stop_after) is not int or stop_after<0):raise ValueError('Invalid pause')
        with writer(self.store.root):
            self.authenticate();self.store.setup();genesis,gid=self._genesis(fault)
            chain=self._recover(self._scan(genesis,gid))
            health=self._health(chain)
            if health is not None:return health
            e=copy.deepcopy(chain['endpoint']);np.random.set_state(e.numpy_global_state)
            rows=[]
            for n in range(chain['n']+1,self.spec['final_sweep']+1):
                if stop_after is not None and n>stop_after:
                    return dict(status='paused',completed=chain['n'],uncommitted=n-1-chain['n'])
                fault('before_sweep');start=time.monotonic()
                try:
                    result=self.layer.sweep(e.state,e.positions,e.tuning,eta_rng=e.eta_rng,
                        gauge_rng=e.gauge_rng,master_key=e.master_key,state_factor_ids=self.target.factor_ids,label=self.store.label(n))
                except (ValueError,RuntimeError,FloatingPointError) as exc:
                    write_json(self.store.segment/'failures'/f'sweep-{n:012d}.json',
                               dict(stage='sweep',sweep=n,last_committed=chain['n'],error=repr(exc)))
                    raise
                elapsed=time.monotonic()-start
                fault('after_sweep')
                rows.append(dict(sweep=n,audit=result.audit,pcg=encode(result.pcg_diagnostics),
                    factors=[dict(index=r['factor_index'],acceptance=np.asarray(r['transition'].info.block_acceptance).tolist(),
                                  divergent=np.asarray(r['transition'].info.block_divergent).tolist(),
                                  leapfrogs=np.asarray(r['transition'].info.block_leapfrogs).tolist()) for r in result.factor_diagnostics]))
                if self.store.input_receipt.get('diagnostics')=='adaptation_study_v1':
                    from .run_health import sweep_measurements
                    rows[-1]['measurements']=sweep_measurements(result,elapsed)
                e=Endpoint(result.state,result.positions,e.tuning,e.eta_rng,e.gauge_rng,
                           result.master_key,np.random.get_state(),self.scale,{})
                print('SWEEP',n,'seconds',round(elapsed,3),'save',self._due(n),flush=True)
                if not self._due(n):continue
                attempt=Path(tempfile.mkdtemp(prefix='periodic-',dir=self.store.segment/'attempts'))
                path=attempt/'boundary';path.mkdir()
                progress=dict(completed_local_sweep=n,settling_sweeps=0,completed_production_sweeps=n,
                              checkpoint_type='complete',status='completed_sweep')
                save_compact(path/'checkpoint.npz',target=self.target,contract=self.cp,result=result,tuning=e.tuning,
                             eta_rng=e.eta_rng,gauge_rng=e.gauge_rng,b_sigma2=self.scale,progress=progress)
                fault('after_checkpoint_candidate')
                write_npz(path/'record.npz',make_completed(self.target,self.rc,self.scale,result,sweep=n,
                    retained_index=chain['retained']+1,previous_sha256=chain['record_head'],events=[],elapsed_seconds=None))
                fault('after_record_candidate')
                write_json(path/'diagnostics.json',rows)
                receipt=dict(schema='bsfm.periodic-boundary.v1',spec_sha256=self.store.spec_hash,sweep=n,
                    previous=chain['head'],files={name:file_record(path/name) for name in ('checkpoint.npz','record.npz','diagnostics.json')})
                receipt['sha256']=digest(receipt);write_json(path/'receipt.json',receipt)
                candidate=self._read_boundary(path,chain)
                fault('before_boundary_publish')
                publish(path,self.store.segment/'boundaries'/f'{n:012d}')
                chain=candidate;rows=[]
                fault('after_boundary_publish')
                health=self._health(chain)
                if health is not None:return health
            self.authenticate()
            closure=dict(schema='bsfm.periodic-completion.v1',completed=chain['n'],retained=chain['retained'],
                         head=chain['head'],spec_sha256=self.store.spec_hash,convergence='not_assessed')
            dest=self.store.segment/'completion.json'
            if dest.exists():
                if read_json(dest)!=closure:raise ValueError('Periodic completion changed')
            else:
                tmp=Path(tempfile.mkdtemp(prefix='closure-',dir=self.store.segment/'attempts'))/'completion.json'
                write_json(tmp,closure);publish(tmp,dest)
            return closure

    def completed_endpoint(self):
        with writer(self.store.root):
            self.authenticate();genesis,gid=self._genesis(lambda stage:None)
            chain=self._scan(genesis,gid);n=chain['n']
            completion=read_json(self.store.segment/'completion.json')
            if n!=self.spec['final_sweep'] or completion['head']!=chain['head'] or completion['completed']!=n:
                raise ValueError('Periodic parent incomplete')
            last=self.store.segment/'boundaries'/f'{n:012d}'
            binding=dict(schema='bsfm.periodic-readaptation-parent.v1',run_id=self.spec['run_id'],
                spec_sha256=self.store.spec_hash,head=chain['head'],completed_sweep=n,
                checkpoint=file_record(last/'checkpoint.npz'),completion=file_record(self.store.segment/'completion.json'),
                pooling='parent bridge draws excluded from child production')
            return copy.deepcopy(chain['endpoint']),binding


class PeriodicRunController(PeriodicMixin, RunController):
    pass


class PeriodicReadaptationController(PeriodicMixin, ReadaptationController):
    pass
