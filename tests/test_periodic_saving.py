"""Real synthetic transitions, compact codec, periodic recovery and scores."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
import numpy as np
from scipy.special import logsumexp
from sampler_layer9_support import controller
from bsfm.sampler.run_periodic import PeriodicRunController,PeriodicReadaptationController
from bsfm.sampler.run_genesis import load_genesis
from bsfm.sampler.compact_checkpoint import load_compact
from bsfm.sampler.checkpoint import load_checkpoint
from bsfm.sampler.run_storage import read_json
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.predictive_summary import PredictiveSummary
from bsfm.sampler.run_readaptation import parent_endpoint


class Stop(BaseException):pass


class PeriodicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.tmp.cleanup)
        cls.root=Path(cls.tmp.name)
        template=Path(os.environ['BSFM_PERIODIC_TEMPLATE'])
        c=controller(template)
        cls.seed,_=load_genesis(template/'segments/segment/genesis/endpoint.npz',c.target,c.cp)
        cls.reference=cls.make(cls.root/'reference');cls.reference.run()

    @classmethod
    def make(cls,root):
        base=controller(root,every=2,final=3)
        c=PeriodicRunController(root,base.target,base.loading,base.eta,base.spec,base.store.input_receipt,
                                authenticate=base.authenticate)
        c.layer=base.layer;c._adapt_endpoint=lambda fault:copy.deepcopy(cls.seed)
        return c

    def test_compact_geometry_omitted_and_boundary_cadence(self):
        c=self.reference;paths=sorted((c.store.segment/'boundaries').iterdir())
        self.assertEqual([p.name for p in paths],['000000000001','000000000002','000000000003'])
        for p in paths:
            with np.load(p/'checkpoint.npz',allow_pickle=False) as z:
                self.assertFalse(any(k.startswith('spectral_') for k in z.files))
            e=load_compact(p/'checkpoint.npz',target=c.target,contract=c.cp)
            self.assertEqual(e.progress['completed_local_sweep'],int(p.name))
        self.assertEqual(list((c.store.segment/'checkpoints').iterdir()),[])

    def test_interruption_before_publication_recomputes_exactly(self):
        for stage in ['after_sweep','after_checkpoint_candidate','before_boundary_publish','after_boundary_publish']:
            with self.subTest(stage=stage):
                c=self.make(self.root/stage)
                def stop(s):
                    if s==stage:raise Stop()
                with self.assertRaises(Stop):c.run(fault=stop)
                c=self.make(self.root/stage);c.run()
                for n in (1,2,3):
                    r=Path('boundaries')/f'{n:012d}'/'receipt.json'
                    self.assertEqual(read_json(c.store.segment/r),read_json(self.reference.store.segment/r))

    def test_completed_nonreplay_and_compact_tamper(self):
        c=self.make(self.root/'reference')
        def fail(*args,**kwargs):raise AssertionError('Replay')
        original=c.layer.sweep;c.layer.sweep=fail
        try:c.run()
        finally:c.layer.sweep=original
        p=c.store.segment/'boundaries/000000000003/checkpoint.npz'
        with np.load(p,allow_pickle=False) as z:d={k:z[k] for k in z.files}
        d['eta']=d['eta'].copy();d['eta'].flat[0]+=1
        bad=self.root/'tampered.npz';np.savez_compressed(bad,**d)
        with self.assertRaises(ValueError):load_compact(bad,target=c.target,contract=c.cp)

    def test_sparse_period_and_parent_binding(self):
        base=controller(self.root/'sparse',every=3,final=4);spec=copy.deepcopy(base.spec);spec['save_every']=3
        c=PeriodicRunController(base.store.root,base.target,base.loading,base.eta,spec,base.store.input_receipt,authenticate=base.authenticate)
        c.layer=base.layer;c._adapt_endpoint=lambda fault:copy.deepcopy(self.seed)
        c.run()
        self.assertEqual([p.name for p in sorted((c.store.segment/'boundaries').iterdir())],['000000000001','000000000003','000000000004'])
        endpoint,binding=parent_endpoint(c)
        self.assertEqual(endpoint.progress['completed_local_sweep'],4)
        self.assertEqual(binding['completed_sweep'],4)

    def test_same_endpoint_as_every_sweep_storage(self):
        c=controller(self.root/'strict',every=2,final=3)
        c._adapt_endpoint=lambda fault:copy.deepcopy(self.seed)
        c.run()
        old=load_checkpoint(c.store.segment/'transactions/000000000003/checkpoint.npz',target=c.target,contract=c.cp)
        new=load_compact(self.reference.store.segment/'boundaries/000000000003/checkpoint.npz',target=c.target,contract=c.cp)
        self.assertEqual(old.logical_sha256,new.logical_sha256)

    def test_unsaved_sweep_recomputed_and_parent_readaptation(self):
        base=controller(self.root/'unsaved',every=3,final=3);spec=copy.deepcopy(base.spec);spec['save_every']=3
        def make():
            c=PeriodicRunController(base.store.root,base.target,base.loading,base.eta,spec,base.store.input_receipt,authenticate=base.authenticate)
            c.layer=base.layer;c._adapt_endpoint=lambda fault:copy.deepcopy(self.seed)
            return c
        c=make();c.run(stop_after=1)
        def stop(stage):
            if stage=='after_sweep':raise Stop()
        with self.assertRaises(Stop):c.run(fault=stop)
        c=make();c.run()
        endpoint,binding=parent_endpoint(c)
        # Verify actual child chronology preserves parent NumPy streams and
        # uses the established readaptation implementation, not initialization.
        child_spec=copy.deepcopy(spec);child_spec.update(run_id='child',final_sweep=1,production_sweeps=1)
        bind=dict(base.store.input_receipt,readaptation_parent=binding);child_spec['input_sha256']=digest(bind)
        child=PeriodicReadaptationController(self.root/'child',c.target,c.loading,c.eta,child_spec,bind,
                                            authenticate=c.authenticate,parent=c)
        from unittest.mock import patch
        with patch('bsfm.sampler.run_readaptation.adapt',side_effect=lambda target,e,keys,**kw:e):
            start=child._adapt_endpoint(lambda stage:None)
        self.assertEqual(start.evidence['initialization']['parent'] if 'initialization' in start.evidence else start.evidence['parent'],binding)
        self.assertEqual(start.eta_rng.bit_generator.state,endpoint.eta_rng.bit_generator.state)


class PredictionTests(unittest.TestCase):
    def test_density_average_not_average_log_or_moment_matched_normal(self):
        y=np.array([[0.,2.]])
        means=[np.array([[0.,0.]]),np.array([[8.,3.]])];vars=[np.ones_like(y),2*np.ones_like(y)]
        s=PredictiveSummary(y)
        for m,v in zip(means,vars):s.update(m,v)
        expected=logsumexp([-.5*(np.log(2*np.pi*v)+(y-m)**2/v) for m,v in zip(means,vars)],axis=0)-np.log(2)
        np.testing.assert_allclose(s.arrays()['pointwise_log_predictive_density'],expected,rtol=1e-14)
        np.testing.assert_allclose(s.arrays()['mean'],np.mean(means,axis=0))
        with self.assertRaises(ValueError):s.update(means[0],np.zeros_like(y))


if __name__=='__main__':unittest.main()
