"""Review-only incremental orchestration under one uninterrupted writer lease.

Not selected by any launcher. Strict public readers and numerical layers stay
unchanged. Full validation occurs on lease entry and closure. File metadata
guards detect ordinary external mutation between boundaries, not adversarial
metadata spoofing or storage corruption that preserves metadata.
"""
import copy
from pathlib import Path
import tempfile
from .run_transactions import Transactions
from .run_storage import (_WRITER_ROOTS, owns_publication, safe, file_record,
                          copy_exact, publish, advisory)
from .checkpoint_contract import digest


class IncrementalTransactions(Transactions):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._lease=None

    def _enter(self):
        lease=_WRITER_ROOTS.get()
        if not owns_publication(self.root,self.root):
            raise RuntimeError('Incremental validation requires the active writer lease')
        # ContextVar tuple identity changes on every acquisition, even for the
        # same PID/root. Cached validation never survives release/reacquisition.
        if lease is not self._lease:
            self._lease=lease;self._chain=None;self._identity=None
            self._files={};self._projected=None;self._projection_files={}

    @staticmethod
    def _stamp(path):
        try:
            s=safe(path).stat()
        except OSError as exc:
            raise ValueError('Previously validated path missing: '+str(path)) from exc
        return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)

    def _remember(self,path,dest):
        dest[Path(path)]=self._stamp(path)

    def _guard(self,files):
        for path,stamp in files.items():
            if self._stamp(path)!=stamp:
                raise ValueError('Previously validated path changed: '+str(path))

    def _remember_transaction(self,path):
        self._remember(path,self._files)
        for name in ('checkpoint.npz','record.npz','prepared.json'):
            self._remember(path/name,self._files)

    def scan(self,genesis,genesis_identity):
        if not owns_publication(self.root,self.root):
            # Ordinary read-only callers retain the original strict semantics.
            self._lease=None
            return super().scan(genesis,genesis_identity)
        self._enter()
        identity=(genesis_identity,self.spec_hash,digest(self.input_receipt))
        if self._chain is None:
            chain=super().scan(genesis,genesis_identity)
            for p in (self.segment/'transactions').iterdir():self._remember_transaction(p)
            for p in (self.root/'run-spec.json',self.root/'input-receipt.json',
                      self.segment/'genesis',self.segment/'genesis/endpoint.npz',
                      self.segment/'genesis/receipt.json'):
                self._remember(p,self._files)
            self._chain=copy.deepcopy(chain);self._identity=identity
            return chain
        if identity!=self._identity:raise ValueError('Incremental chain identity changed')
        self._guard(self._files)
        paths=sorted((self.segment/'transactions').iterdir())
        n=len(self._chain['rows'])
        if len(paths) not in (n,n+1) or any(p.name!=f'{i:012d}' for i,p in enumerate(paths,1)):
            raise ValueError('Gapped/extra incremental transaction namespace')
        if len(paths)==self.spec['final_sweep']:
            chain=super().scan(genesis,genesis_identity)
            for p in paths:self._remember_transaction(p)
            self._chain=copy.deepcopy(chain)
            return chain
        if len(paths)==n+1:
            p=paths[-1]
            if not p.is_dir() or sorted(x.name for x in p.iterdir())!=['checkpoint.npz','prepared.json','record.npz']:
                raise ValueError('Incomplete new committed transaction')
            c=self._chain
            endpoint,m,receipt=self.pair(p,n+1,c['head'],c['record_head'],c['retained'],c['boundary'],c['frozen'])
            c['rows'].append(receipt);c.update(head=receipt['sha256'],record_head=m['logical_sha256'],
                retained=c['retained']+int(m['retained_index'] is not None),boundary=endpoint.boundary,endpoint=endpoint)
            self._remember_transaction(p)
        return copy.deepcopy(self._chain)

    def _remember_projections(self):
        self._projection_files={}
        archive=self.segment/'archive'
        self._remember(archive/'contract.json',self._projection_files)
        for p in (archive/'records').iterdir():
            if p.name.startswith('.attempt-'):continue
            self._remember(p,self._projection_files)
            self._remember(p/'record.npz',self._projection_files)
        for p in (self.segment/'checkpoints').iterdir():
            if not p.name.startswith('.attempt-'):self._remember(p,self._projection_files)

    def repair(self,chain,fault):
        self._enter();count=len(chain['rows'])
        if self._chain is None or chain['head']!=self._chain['head']:
            raise ValueError('Projection repair requires the validated current chain')
        self._guard(self._files)
        if self._projected is None or count==self.spec['final_sweep']:
            # Public archive type is returned only after complete validation.
            view=super().repair(chain,fault)
            self._remember_projections();self._projected=count
            return view
        self._guard(self._projection_files)
        if count not in (self._projected,self._projected+1):
            raise ValueError('Unexpected incremental projection advance')
        archive=self.segment/'archive'
        expected={f'{i:012d}' for i in range(1,count+1)}
        names={p.name for p in (archive/'records').iterdir() if not p.name.startswith('.attempt-')}
        if not names.issubset(expected):raise ValueError('Orphan archive projection')
        wanted={f'{i:012d}.npz' for i in range(1,count+1)
                if i%self.spec['checkpoint_every']==0 or i==self.spec['final_sweep']}
        names={p.name for p in (self.segment/'checkpoints').iterdir() if not p.name.startswith('.attempt-')}
        if not names.issubset(wanted):raise ValueError('Orphan checkpoint projection')
        if count>self._projected:
            src=self.segment/'transactions'/f'{count:012d}'
            dst=archive/'records'/f'{count:012d}'
            if dst.exists():
                if sorted(p.name for p in dst.iterdir())!=['record.npz'] or file_record(dst/'record.npz')!=chain['rows'][-1]['record']:
                    raise ValueError('Conflicting archive projection')
            else:
                tmp=Path(tempfile.mkdtemp(prefix='.attempt-',dir=archive/'records'))
                copy_exact(src/'record.npz',tmp/'record.npz');publish(tmp,dst)
            # Exact bytes of an independently validated new transaction; no
            # historical numerical revalidation hidden in the live view.
            if file_record(dst/'record.npz')!=chain['rows'][-1]['record']:
                raise ValueError('New record projection failed readback')
            self._remember(dst,self._projection_files)
            self._remember(dst/'record.npz',self._projection_files)
            fault('after_record_projection')
            if f'{count:012d}.npz' in wanted:
                cp=self.segment/'checkpoints'/f'{count:012d}.npz'
                copy_exact(src/'checkpoint.npz',cp)
                if file_record(cp)!=chain['rows'][-1]['checkpoint']:raise ValueError('New checkpoint projection failed readback')
                self._remember(cp,self._projection_files)
            fault('after_checkpoint_projection')
            self._projected=count
        fault('before_ledger')
        advisory(self.segment/'run-ledger.json',dict(head=chain['head'],completed=count,retained=chain['retained']))
        return None  # Deliberately not represented as a fully reopened archive.
