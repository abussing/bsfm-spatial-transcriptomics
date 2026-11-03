"""Pure bookkeeping counts with fake validators; not numerical/restart evidence."""
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from bsfm.sampler.run_incremental import IncrementalTransactions
from bsfm.sampler.run_transactions import Transactions
from bsfm.sampler.run_storage import writer


class BookkeepingTests(unittest.TestCase):
    def test_numerical_pair_calls_scale_linearly_in_live_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'run';seg=root/'segments/segment'
            (seg/'transactions').mkdir(parents=True);(seg/'genesis').mkdir()
            for p in [root/'run-spec.json',root/'input-receipt.json',seg/'genesis/endpoint.npz',seg/'genesis/receipt.json']:
                p.write_text('synthetic bookkeeping placeholder')
            stores=[]
            for cls in (Transactions,IncrementalTransactions):
                s=object.__new__(cls);s.root=root;s.segment=seg;s.spec_hash='spec';s.input_receipt={}
                s.spec={'final_sweep':100};s.rc=SimpleNamespace(sha256='record0');s.target=None;s._lease=None
                stores.append(s)
            def pair(path,n,*args):
                return SimpleNamespace(boundary={}),{'logical_sha256':str(n),'retained_index':n},{'sha256':str(n)}
            genesis=SimpleNamespace(tuning=[])
            with writer(root),patch('bsfm.sampler.run_transactions.boundary',return_value={}), \
                 patch.object(stores[0],'pair',side_effect=pair) as old,patch.object(stores[1],'pair',side_effect=pair) as new:
                stores[1].scan(genesis,'genesis')
                for n in range(1,51):
                    p=seg/'transactions'/f'{n:012d}';p.mkdir()
                    for name in ['checkpoint.npz','record.npz','prepared.json']: (p/name).write_text('placeholder')
                    a=stores[0].scan(genesis,'genesis');b=stores[1].scan(genesis,'genesis')
                    self.assertEqual(a['head'],b['head']);self.assertEqual(a['retained'],b['retained'])
                    self.assertEqual(old.call_count,n*(n+1)//2)
                    self.assertEqual(new.call_count,n)
                print('BOOKKEEPING_PAIR_COUNTS strict=1275 incremental=50 at prefix=50; fake validators only',flush=True)
