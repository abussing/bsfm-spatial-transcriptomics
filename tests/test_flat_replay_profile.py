"""A timing observer must preserve the original flat transition and RNG."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
import jax
import numpy as np
from test_flat_range import setup
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.flat_replay_profile import timed_calls, compare_diagnostics, require_original_coordinates

class FlatReplayProfileTests(unittest.TestCase):
    def test_reject_alternate_coordinates(self):
        require_original_coordinates({})
        require_original_coordinates({'transition_policy': None})
        with self.assertRaisesRegex(ValueError, 'Original flat'):
            require_original_coordinates({'transition_policy': {'name': 'flat_variances_v1'}})

    def test_restore_after_exception_without_consuming_rng(self):
        rng=np.random.default_rng(718)
        obj=SimpleNamespace(f=lambda: rng.normal(size=3))
        original=obj.f; rows=[]
        with self.assertRaisesRegex(RuntimeError,'stop'):
            with timed_calls([(obj,'f','draw')],rows):
                value=obj.f()
                raise RuntimeError('stop')
        self.assertIs(obj.f,original)
        expected=np.random.default_rng(718)
        np.testing.assert_array_equal(value,expected.normal(size=3))
        np.testing.assert_array_equal(obj.f(),expected.normal(size=3))
        self.assertEqual(len(rows),1)

    def test_actual_flat_transition_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/'run'); e,_=initialize(c.target,c.loading,c.eta,seed=491)
            split=c.layer.split; p=e.positions[0]
            tuning=split.tuning(p.factor_id,step_size=.01)
            kwargs=dict(state_factor_ids=c.target.factor_ids)
            key=jax.random.PRNGKey(938)
            first=split.transition(key,p,e.state,tuning,**kwargs)
            rows=[]
            with timed_calls([(split,'transition','nuts')],rows):
                second=split.transition(key,p,e.state,tuning,**kwargs)
            np.testing.assert_array_equal(first.position.values,second.position.values)
            for name in ('block_acceptance','block_divergent','block_leapfrogs','momentum'):
                np.testing.assert_array_equal(getattr(first.info,name),getattr(second.info,name))
            self.assertEqual(len(rows),1)

    def test_authentication_catches_mismatches(self):
        x=dict(acceptance=[.8,0.],divergent=[False,False],leapfrogs=[15,0])
        self.assertTrue(compare_diagnostics(x,x)['matches_recorded_transition'])
        for key,value in [('acceptance',[.7,0.]),('divergent',[True,False]),('leapfrogs',[31,0])]:
            self.assertFalse(compare_diagnostics(dict(x,**{key:value}),x)['matches_recorded_transition'])
