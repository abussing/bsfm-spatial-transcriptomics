"""Whole-directory sweep commits; immutable authority, repairable projections."""
import os
from pathlib import Path
import re
import tempfile
import uuid
import zipfile
from .checkpoint import load_checkpoint
from .checkpoint_contract import digest
from .checkpoint_rng import json_text, parse_json
from .retained_records import load_record
from .retained_contract import retain_at
from .retained_archive import create_archive, RetainedArchive
from .run_genesis import boundary
from .run_storage import safe, file_record, read_json, write_json, publish, copy_exact, advisory


def tuning_identity(tuning):
    return [dict(factor_id=t.factor_id,step=t.step_size,hyper_step=t.hyper_step_size,mass=t.mass_sha256) for t in tuning]


class Transactions:
    def __init__(self,root,target,checkpoint_contract,archive_contract,scale,spec,input_receipt):
        self.root=safe(root);self.target=target;self.cp=checkpoint_contract;self.rc=archive_contract
        self.scale=scale;self.spec=spec;self.spec_hash=digest(spec);self.input_receipt=input_receipt
        self.segment=self.root/'segments'/spec['segment_id'];self.records=parse_json(archive_contract.json)

    def setup(self):
        for name,value in [('run-spec.json',self.spec),('input-receipt.json',self.input_receipt)]:
            path=self.root/name
            if path.exists():
                if read_json(path)!=value:raise ValueError('Immutable run/input identity changed')
            else:
                attempt=self.root/('.attempt-'+name+'-'+uuid.uuid4().hex)
                write_json(attempt,value);publish(attempt,path)
        self.segment.mkdir(parents=True,exist_ok=True)
        for name in ('attempts','transactions','checkpoints','failures'):(self.segment/name).mkdir(exist_ok=True)
        if list((self.segment/'failures').iterdir()):raise ValueError('Recorded terminal failure; no automatic retry')

    def label(self,n):return f"{self.spec['run_id']}/{self.spec['segment_id']}/{self.spec['chain_id']}/{n:012d}"

    def pair(self,path,n,previous,record_previous,retained,prior,frozen):
        """Independent public Layer-7/8 readers, then cross-boundary authentication."""
        path=safe(path)
        cp=load_checkpoint(path/'checkpoint.npz',target=self.target,contract=self.cp)
        m,_,d=load_record(path/'record.npz',target=self.target,contract=self.rc,b_sigma2=self.scale)
        if (m['status']!='completed' or m['sweep']!=n or m['previous_sha256']!=record_previous
            or cp.progress['completed_local_sweep']!=n
            or cp.progress['settling_sweeps']!=self.spec['settling_sweeps']
            or cp.progress['completed_production_sweeps']!=m['production_sweep']
            or d['elapsed_seconds'] is not None or d['sweep_audit']['label']!=self.label(n)):
            raise ValueError('Transaction progress/record mismatch')
        expected_index=retained+1 if retain_at(self.records,n) else None
        if m['retained_index']!=expected_index:raise ValueError('Retention chronology mismatch')
        a=d['sweep_audit']
        for before,after in [('state_before','state_after'),('positions_before','positions_after'),('rng_before','rng_after')]:
            if a[before]!=prior[after]:raise ValueError('Transaction predecessor boundary mismatch')
        if any(a.get(k)!=v for k,v in cp.boundary.items()):raise ValueError('Record/checkpoint boundary mismatch')
        if tuning_identity(cp.tuning)!=frozen:raise ValueError('Frozen tuning changed')
        body=dict(schema='bsfm.sweep-transaction.v1',spec_sha256=self.spec_hash,input_sha256=digest(self.input_receipt),
            checkpoint_contract_sha256=self.cp.sha256,archive_contract_sha256=self.rc.sha256,
            sweep=n,previous_sha256=previous,checkpoint=file_record(path/'checkpoint.npz'),
            record=file_record(path/'record.npz'),checkpoint_logical_sha256=cp.logical_sha256,
            record_logical_sha256=m['logical_sha256'],joint_validation='pass')
        body['sha256']=digest(body)
        if (path/'prepared.json').exists() and read_json(path/'prepared.json')!=body:raise ValueError('Prepared receipt mismatch')
        return cp,m,body

    def scan(self,genesis,genesis_identity):
        head=digest(dict(spec=self.spec_hash,input=digest(self.input_receipt),genesis=genesis_identity))
        previous_record=self.rc.sha256;retained=0;prior=boundary(genesis,self.target);rows=[];last=genesis
        paths=sorted((self.segment/'transactions').iterdir())
        frozen=tuning_identity(genesis.tuning)
        for n,p in enumerate(paths,1):
            if p.name!=f'{n:012d}' or not p.is_dir() or sorted(x.name for x in p.iterdir())!=['checkpoint.npz','prepared.json','record.npz']:
                raise ValueError('Gapped/extra/incomplete committed transaction')
            last,m,receipt=self.pair(p,n,head,previous_record,retained,prior,frozen)
            rows.append(receipt);head=receipt['sha256'];previous_record=m['logical_sha256']
            retained+=int(m['retained_index'] is not None);prior=last.boundary
        return dict(head=head,record_head=previous_record,retained=retained,boundary=prior,
                    rows=rows,endpoint=last,frozen=frozen)

    def recover_prepared(self,chain,fault):
        n=len(chain['rows'])+1;candidates=[]
        for attempt in sorted((self.segment/'attempts').iterdir()):
            intent=attempt/'intent.json';p=attempt/'transaction'
            if not intent.exists():continue
            try:value=read_json(intent)
            except ValueError:
                if (p/'prepared.json').exists():raise
                continue # torn pre-sweep intent is not a completed pair
            if value['sweep']<n:continue # older attempts never displace a committed transaction
            if value!=dict(sweep=n,previous_sha256=chain['head'],spec_sha256=self.spec_hash):
                raise ValueError('Conflicting/stale future attempt')
            if not (p/'checkpoint.npz').exists() or not (p/'record.npz').exists():continue
            # Two complete but invalid files are not permission to replay silently.
            try:
                _,_,receipt=self.pair(p,n,chain['head'],chain['record_head'],chain['retained'],chain['boundary'],chain['frozen'])
            except (EOFError,zipfile.BadZipFile):
                if (p/'prepared.json').exists():raise
                continue # interrupted file write; preserve and recompute uncommitted sweep
            candidates.append((p,receipt))
        if len(candidates)>1:raise ValueError('Multiple prepared next transactions; review required')
        if not candidates:return False
        p,receipt=candidates[0]
        if not (p/'prepared.json').exists():write_json(p/'prepared.json',receipt)
        if sorted(x.name for x in p.iterdir())!=['checkpoint.npz','prepared.json','record.npz']:raise ValueError('Unexpected candidate files')
        fault('before_transaction_publish');publish(p,self.segment/'transactions'/f'{n:012d}');fault('after_transaction_publish')
        return True

    def repair(self,chain,fault):
        count=len(chain['rows']);archive=self.segment/'archive'
        if not archive.exists():
            temp=Path(tempfile.mkdtemp(prefix='archive-',dir=self.segment/'attempts'))/'archive'
            create_archive(temp,target=self.target,contract=self.rc,b_sigma2=self.scale);publish(temp,archive)
        if read_json(archive/'contract.json')!=parse_json(self.rc.json):raise ValueError('Projection contract mismatch')
        for p in (archive/'records').iterdir():
            safe(p)
            if p.name.startswith('.attempt-'):continue
            if not re.fullmatch(r'\d{12}',p.name) or not 1<=int(p.name)<=count:raise ValueError('Orphan archive projection')
        wanted={n for n in range(1,count+1) if n%self.spec['checkpoint_every']==0 or n==self.spec['final_sweep']}
        for p in (self.segment/'checkpoints').iterdir():
            safe(p)
            if p.name.startswith('.attempt-'):continue
            if p.name not in {f'{n:012d}.npz' for n in wanted}:raise ValueError('Orphan checkpoint projection')
        for n in range(1,count+1):
            src=self.segment/'transactions'/f'{n:012d}';dst=archive/'records'/f'{n:012d}'
            if dst.exists():
                if sorted(p.name for p in dst.iterdir())!=['record.npz'] or file_record(dst/'record.npz')!=file_record(src/'record.npz'):raise ValueError('Conflicting archive projection')
            else:
                tmp=Path(tempfile.mkdtemp(prefix='.attempt-',dir=archive/'records'))
                copy_exact(src/'record.npz',tmp/'record.npz');publish(tmp,dst)
            fault('after_record_projection')
            if n in wanted:copy_exact(src/'checkpoint.npz',self.segment/'checkpoints'/f'{n:012d}.npz')
            fault('after_checkpoint_projection')
        view=RetainedArchive(archive,target=self.target,contract=self.rc,b_sigma2=self.scale)
        if count:view.require_resume_boundary(chain['endpoint'])
        fault('before_ledger');advisory(self.segment/'run-ledger.json',dict(head=chain['head'],completed=count,retained=chain['retained']))
        return view
