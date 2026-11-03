"""Single-writer append-only sweep records, independent of restart checkpoints."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .checkpoint_rng import json_text, parse_json
from .checkpoint_contract import digest
from .retained_contract import validate_retained_contract, retain_at
from .retained_records import make_completed, make_failure, load_record
from .layer4 import state_hashes
from .contracts import logical_hash
from .checkpoint_rng import stream_audit
from .retained_diagnostics import encode


def _continuous(previous, current):
    if previous is None or current['status']=='failed': return
    before=current['diagnostics']['sweep_audit']
    after=previous['diagnostics']['sweep_audit']
    for left,right in (('state_before','state_after'),('positions_before','positions_after'),('rng_before','rng_after')):
        if before[left]!=after[right]: raise ValueError('Discontinuous sampler state/chart/RNG boundary')


class ArchiveWriteError(RuntimeError):
    def __init__(self, attempt):
        self.attempt=Path(attempt)
        super().__init__('Record not promoted; attempt retained: '+str(attempt))


def _write_npz(path, data):
    with Path(path).open('xb') as stream:
        np.savez_compressed(stream,**data)
        stream.flush();os.fsync(stream.fileno())


def create_archive(root, *, target, contract, b_sigma2):
    validate_retained_contract(contract,target,b_sigma2)
    root=Path(root);root.mkdir()  # Fresh root only; never overwrite an archive.
    attempt=root/'.contract.attempt'
    with attempt.open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(contract.json+'\n');stream.flush();os.fsync(stream.fileno())
    if parse_json(attempt.read_text(encoding='utf-8'))!=parse_json(contract.json):
        raise ValueError('Contract readback failed')
    os.rename(attempt,root/'contract.json')
    (root/'records').mkdir()
    return RetainedArchive(root,target=target,contract=contract,b_sigma2=b_sigma2)


class RetainedArchive:
    """Validated archive handle. No sampler loop, checkpoint writes or implicit resume.

    Each published directory contains one fully validated record.npz. Atomic
    directory rename cannot replace an existing nonempty record directory.
    One cooperating writer is supported; external deletion/tampering is rejected
    by full revalidation and hashes, not defended against as an adversary.
    """
    def __init__(self, root, *, target, contract, b_sigma2):
        self.root=Path(root);self.target=target;self.contract=contract
        self.b_sigma2=np.array(b_sigma2,copy=True);self.b_sigma2.flags.writeable=False
        self.spec=validate_retained_contract(contract,target,self.b_sigma2)
        self.records=[]
        self.validate()

    def _paths(self):
        if (self.root/'contract.json').read_text(encoding='utf-8')!=self.contract.json+'\n':
            raise ValueError('Archive contract mismatch')
        names=[]
        for p in (self.root/'records').iterdir():
            if p.name.startswith('.attempt-'): continue  # Never consumed as completion.
            if not p.is_dir() or len(p.name)!=12 or not p.name.isdecimal():
                raise ValueError('Unexpected published record path')
            names.append(p)
        return sorted(names)

    def validate(self):
        """Reopen every published file; no RNG/state mutation or cached authority."""
        previous=self.contract.sha256;retained=0;records=[]
        for i,path in enumerate(self._paths(),1):
            if path.name!=f'{i:012d}' or sorted(p.name for p in path.iterdir())!=['record.npz']:
                raise ValueError('Missing/out-of-order/incomplete published record')
            if records and records[-1]['status']=='failed': raise ValueError('Completion after terminal failure')
            m,_,_=load_record(path/'record.npz',target=self.target,contract=self.contract,b_sigma2=self.b_sigma2)
            if m['sweep']!=i or m['previous_sha256']!=previous: raise ValueError('Archive chronology/hash-chain mismatch')
            _continuous(records[-1] if records else None,m)
            if m['retained_index'] is not None:
                retained+=1
                if m['retained_index']!=retained: raise ValueError('Skipped/duplicate retained index')
            records.append(m);previous=m['logical_sha256']
        self.records=records
        return dict(records=len(records),retained=retained,head_sha256=previous,
                    status='failed' if records and records[-1]['status']=='failed' else 'valid_prefix',
                    attempts=[str(p) for p in sorted((self.root/'records').glob('.attempt-*'))])

    def _next(self):
        # Detect stale handles/competing publication; no silent overwrite/retry.
        if len(self._paths())!=len(self.records): raise ValueError('Archive advanced; reopen and validate')
        if self.records and self.records[-1]['status']=='failed': raise ValueError('Terminal failure; no implicit retry')
        return len(self.records)+1, self.records[-1]['logical_sha256'] if self.records else self.contract.sha256

    def _promote(self,data,sweep):
        attempt=Path(tempfile.mkdtemp(prefix='.attempt-',dir=self.root/'records'))
        try:
            _write_npz(attempt/'record.npz',data)
            m,_,_=load_record(attempt/'record.npz',target=self.target,contract=self.contract,b_sigma2=self.b_sigma2)
            expected,previous=self._next()
            if sweep!=expected or m['previous_sha256']!=previous: raise ValueError('Stale candidate record')
            _continuous(self.records[-1] if self.records else None,m)
            final=self.root/'records'/f'{sweep:012d}'
            if final.exists(): raise FileExistsError(final)
            # A published target is nonempty; rename cannot replace it on
            # supported Windows or POSIX filesystems. No os.replace of draws.
            os.rename(attempt,final)
        except Exception as exc:
            raise ArchiveWriteError(attempt) from exc
        self.records.append(m)
        return dict(sweep=sweep,retained_index=m['retained_index'],logical_sha256=m['logical_sha256'])

    def append(self,result,*,sweep,events,elapsed_seconds):
        expected,previous=self._next()
        if type(sweep) is not int or sweep!=expected: raise ValueError('Duplicate/skipped/out-of-order sweep')
        index=1+sum(r['retained_index'] is not None for r in self.records)
        data=make_completed(self.target,self.contract,self.b_sigma2,result,sweep=sweep,
            retained_index=index,previous_sha256=previous,events=events,elapsed_seconds=elapsed_seconds)
        return self._promote(data,sweep)

    def record_failure(self,*,attempted_sweep,events,partial_diagnostics):
        expected,previous=self._next()
        if type(attempted_sweep) is not int or attempted_sweep!=expected: raise ValueError('Wrong attempted sweep')
        data=make_failure(self.contract,sweep=expected,previous_sha256=previous,
                          events=events,partial_diagnostics=partial_diagnostics)
        return self._promote(data,expected)

    def require_resume_boundary(self,restart):
        """Reject checkpoint/archive disagreement; never truncate, merge or skip."""
        self.validate()
        if not self.records or self.records[-1]['status']!='completed': raise ValueError('Completed archive boundary required')
        m=self.records[-1]
        if (restart.contract.sha256!=self.spec['continuation_sha256']
                or restart.progress['completed_local_sweep']!=m['sweep']
                or restart.progress['settling_sweeps']!=self.spec['retention']['settling_sweeps']
                or restart.progress['completed_production_sweeps']!=m['production_sweep']):
            raise ValueError('Checkpoint/archive contract or progress mismatch')
        audit=m['diagnostics']['sweep_audit']
        if (state_hashes(restart.state)!=restart.boundary['state_after']
                or [logical_hash(p.values) for p in restart.positions]!=restart.boundary['positions_after']
                or stream_audit(restart.eta_rng,restart.gauge_rng,restart.master_key,restart.numpy_global_state)!=restart.boundary['rng_after']):
            raise ValueError('Restart object changed after checkpoint validation')
        for name,value in restart.boundary.items():
            if audit.get(name)!=value: raise ValueError('Checkpoint/archive endpoint mismatch')
        return True

    def read_retained(self,index):
        if type(index) is not int or index<1: raise ValueError('One-based retained index required')
        self.validate()
        matches=[r for r in self.records if r['retained_index']==index]
        if len(matches)!=1: raise ValueError('Retained index not present')
        return load_record(self.root/'records'/f"{matches[0]['sweep']:012d}"/'record.npz',
                           target=self.target,contract=self.contract,b_sigma2=self.b_sigma2)


def aggregate_archives(archives):
    """Offline raw diagnostics only. No ESS/R-hat, alignment or convergence claim."""
    if not archives: raise ValueError('At least one explicit archive required')
    chains={};common=None
    for a in archives:
        summary=a.validate();chain=a.spec['chain_id']
        identity=json_text(a.spec['continuation_contract'])
        if chain in chains or (common is not None and identity!=common):
            raise ValueError('Duplicate chain or incompatible target/software/run identities')
        common=identity;rows=[];pcg=[];px=[];div=np.zeros(2,dtype=int);accept=[];energies=[];events=[]
        for m in a.records:
            _,_,d=load_record(a.root/'records'/f"{m['sweep']:012d}"/'record.npz',
                              target=a.target,contract=a.contract,b_sigma2=a.b_sigma2)
            events.extend(dict(sweep=m['sweep'],**e) for e in d['events'])
            if m['status']=='failed': continue
            pcg.extend(d['pcg']);px.extend(d['px']['checks_relative'].values())
            for f in d['factors']:
                info=f['info'];div+=np.asarray(info['block_divergent'],int)
                accept.append(np.asarray(info['block_acceptance'],float))
                # Per-transition block energies, never combined as one Hamiltonian.
                energies.append(dict(sweep=m['sweep'],factor_id=f['factor_id'],
                                     block_order=['field','hyper'],
                                     block_energy=encode([float(v) for v in info['block_energy']])))
            rows.append(dict(sweep=m['sweep'],retained_index=m['retained_index'],
                             factor_order=d['factor_order'],elapsed_seconds=d['elapsed_seconds']))
        chains[chain]=dict(status=summary['status'],records=summary['records'],retained=summary['retained'],
            head_sha256=summary['head_sha256'],rows=rows,events=events,block_energy=energies,
            divergence_counts=div.tolist(),mean_block_acceptance=np.mean(accept,axis=0).tolist() if accept else None,
            pcg_iterations=[r['iterations'] for r in pcg],
            pcg_max_error_bound=max((r['posterior_mahalanobis_RMS_error_upper_bound'] for r in pcg),default=None),
            px_max_invariant_error=max(px,default=None),fidelity_status='not_evaluated_by_layers_1_to_8')
    result=dict(schema='bsfm.raw-diagnostic-aggregate.v1',chains={k:chains[k] for k in sorted(chains)},
                convergence_status='not_assessed',energy_semantics='separate field/hyper conditional Hamiltonians; no pooled BFMI',
                factor_alignment='native labels; no cross-chain factor posterior pooling')
    result['logical_sha256']=digest(result)
    return result
