"""Run the existing complete Layer-9 fault matrix against the review-only store."""
import copy
from pathlib import Path
import shutil
import tempfile
from unittest.mock import patch
import test_sampler_layer9 as baseline
from bsfm.sampler.run_incremental import IncrementalTransactions
from bsfm.sampler.run_storage import writer,read_json
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.run_transactions import Transactions


class IncrementalTests(baseline.Layer9Tests):
    @classmethod
    def setUpClass(cls):
        cls.reference_tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.reference_tmp.cleanup)
        cls.strict_root=Path(cls.reference_tmp.name)/'strict'
        strict=baseline.controller(cls.strict_root)
        cls.strict_completion=strict.run()
        replacement=patch('bsfm.sampler.run_controller.Transactions',IncrementalTransactions)
        replacement.start();cls.addClassCleanup(replacement.stop)
        super().setUpClass()

    def test_strict_and_incremental_actual_results_exact(self):
        self.assertEqual(self.complete,self.strict_completion)
        for i in (1,2):
            rel=Path('segments/segment/transactions')/f'{i:012d}'/'prepared.json'
            self.assertEqual(read_json(self.template/rel),read_json(self.strict_root/rel))

    def test_no_cached_authority_outside_writer(self):
        c=self.copy_prefix(1)
        with patch.object(c.store,'pair',wraps=c.store.pair) as pair:
            c.store.scan(self.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))
            c.store.scan(self.genesis,digest(read_json(c.store.segment/'genesis/receipt.json')))
            self.assertEqual(pair.call_count,2)

    def test_prior_numerical_validation_not_repeated_within_lease(self):
        c=self.copy_prefix(1);gid=digest(read_json(c.store.segment/'genesis/receipt.json'))
        with writer(c.store.root),patch.object(c.store,'pair',wraps=c.store.pair) as pair:
            first=c.store.scan(self.genesis,gid);self.assertEqual(pair.call_count,1)
            c.store.repair(first,lambda _:None)
            for _ in range(5):
                chain=c.store.scan(self.genesis,gid);self.assertEqual(chain['head'],first['head'])
                self.assertIsNone(c.store.repair(chain,lambda _:None))
            self.assertEqual(pair.call_count,1)
        # A new lease on the SAME object must perform full numerical validation.
        with writer(c.store.root),patch.object(c.store,'pair',wraps=c.store.pair) as pair:
            c.store.scan(self.genesis,gid);self.assertEqual(pair.call_count,1)

    def test_mutation_during_lease_is_rejected(self):
        c=self.copy_prefix(1);gid=digest(read_json(c.store.segment/'genesis/receipt.json'))
        with writer(c.store.root):
            c.store.scan(self.genesis,gid)
            p=c.store.segment/'transactions/000000000001/record.npz'
            with p.open('ab') as f:f.write(b'corruption')
            with self.assertRaisesRegex(ValueError,'changed'):c.store.scan(self.genesis,gid)

    def test_projection_mutation_during_lease_is_rejected(self):
        c=self.copy_prefix(1);gid=digest(read_json(c.store.segment/'genesis/receipt.json'))
        with writer(c.store.root):
            chain=c.store.scan(self.genesis,gid);c.store.repair(chain,lambda _:None)
            p=c.store.segment/'archive/records/000000000001/record.npz'
            with p.open('ab') as f:f.write(b'corruption')
            with self.assertRaisesRegex(ValueError,'changed'):c.store.repair(chain,lambda _:None)

    def test_genesis_mutation_during_lease_is_rejected(self):
        c=self.copy_prefix(1);gid=digest(read_json(c.store.segment/'genesis/receipt.json'))
        with writer(c.store.root):
            c.store.scan(self.genesis,gid)
            with (c.store.segment/'genesis/endpoint.npz').open('ab') as f:f.write(b'corruption')
            with self.assertRaisesRegex(ValueError,'changed'):c.store.scan(self.genesis,gid)
