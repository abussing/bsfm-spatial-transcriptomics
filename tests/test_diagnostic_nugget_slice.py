"""Diagnostic slice adapter: original chart, immutable input and full-Gibbs integration."""
import copy
import tempfile
import unittest
from pathlib import Path
import jax
import numpy as np
from test_flat_range import setup
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.diagnostic_nugget_slice import DiagnosticNuggetSlice
from bsfm.sampler.layer6 import GibbsSweep
from bsfm.sampler.contracts import logical_hash

class DiagnosticNuggetSliceTests(unittest.TestCase):
    def test_repeatable_original_chart_transition_and_unchanged_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/"unused");t=c.target
            ep,_=initialize(t,c.loading,c.eta,seed=491)
            tr=DiagnosticNuggetSlice(t)
            position=ep.positions[0]
            tuning=tr.tuning(position.factor_id,step_size=.03,hyper_step_size=1.,
                              inverse_mass_matrix=np.ones(3))
            before=logical_hash(ep.state.eta)
            key=jax.random.PRNGKey(181)
            a=tr.transition(key,position,ep.state,tuning,state_factor_ids=t.factor_ids)
            b=tr.transition(key,position,ep.state,tuning,state_factor_ids=t.factor_ids)
            np.testing.assert_array_equal(a.position.values,b.position.values)
            self.assertEqual(before,logical_hash(ep.state.eta))
            value,grad,_=t.value_grad(a.position,ep.state,state_factor_ids=t.factor_ids)
            np.testing.assert_allclose(a.nuts_state.logdensity,value,atol=1e-10)
            np.testing.assert_allclose(a.nuts_state.logdensity_grad,grad,atol=1e-9)
            self.assertGreater(a.audit["slice_cost"]["evaluations"],1)

    def test_full_gibbs_sweep_preserves_context_checks_and_repeats(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/"unused");t=c.target
            ep,_=initialize(t,c.loading,c.eta,seed=491)
            layer=GibbsSweep(t,b_sigma2=ep.b_sigma2)
            tr=DiagnosticNuggetSlice(t);layer.split=tr
            tunings=[]
            for i,p in enumerate(ep.positions):
                tuning,_=tr.fit_tuning(jax.random.PRNGKey(10+i),p,ep.state,
                                      steps=20,maximum_seconds=60)
                tunings.append(tuning)
            results=[]
            for _ in range(2):
                e=copy.deepcopy(ep);np.random.set_state(e.numpy_global_state)
                results.append(layer.sweep(e.state,e.positions,tuple(tunings),
                    eta_rng=e.eta_rng,gauge_rng=e.gauge_rng,master_key=e.master_key,
                    state_factor_ids=t.factor_ids,label="synthetic slice diagnostic"))
            np.testing.assert_array_equal(results[0].fitted_Y,results[1].fitted_Y)
            for a,b in zip(results[0].positions,results[1].positions):
                np.testing.assert_array_equal(a.values,b.values)
            self.assertTrue(np.isfinite(results[0].fitted_Y).all())

