"""A diagnostic checkpoint must reproduce the next complete Gibbs sweep."""
import copy
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
import jax
jax.config.update("jax_enable_x64",True)
import numpy as np
from test_flat_range import setup
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.flat_control import FlatTransition
from bsfm.sampler.coordinate_transition import VarianceTransition
from bsfm.sampler.diagnostic_nugget_slice import DiagnosticNuggetSlice
from bsfm.sampler.diagnostic_flat_checkpoint import save_endpoint,load_endpoint
from bsfm.sampler.layer6 import GibbsSweep,state_hashes
from bsfm.sampler.checkpoint_rng import stream_audit
from bsfm.sampler.run_health import review_windows

class DiagnosticCheckpointTests(unittest.TestCase):
    def test_roundtrip_next_sweep_and_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/"source");target=c.target
            initial,_=initialize(target,c.loading,c.eta,seed=491)
            for method in ("original_joint","variance_joint","nugget_slice"):
                if method=="original_joint":transition=FlatTransition(target)
                elif method=="variance_joint":transition=VarianceTransition(target,dict(name="flat_variances_v1"))
                else:transition=DiagnosticNuggetSlice(target,depth=10)
                ep=copy.deepcopy(initial)
                ep.tuning=tuple(transition.tuning(fid,step_size=.01,hyper_step_size=1.)
                                for fid in target.factor_ids)
                path=Path(tmp)/(method+".npz")
                save_endpoint(path,ep,target,transition,method=method,plan_hash="test",sweep=7,epoch=1)
                restored,meta=load_endpoint(path,target,transition,method=method,plan_hash="test")
                self.assertEqual(meta["sweep"],7)
                self.assertEqual(meta["epoch"],1)
                with self.assertRaises(ValueError):
                    load_endpoint(path,target,transition,method=method,plan_hash="wrong")
                results=[]
                streams=[]
                for e in (ep,restored):
                    layer=GibbsSweep(target,b_sigma2=e.b_sigma2);layer.split=transition
                    np.random.set_state(e.numpy_global_state)
                    result=layer.sweep(e.state,e.positions,e.tuning,eta_rng=e.eta_rng,
                        gauge_rng=e.gauge_rng,master_key=e.master_key,
                        state_factor_ids=target.factor_ids,label="checkpoint-test")
                    results.append(result)
                    streams.append(stream_audit(e.eta_rng,e.gauge_rng,result.master_key,np.random.get_state()))
                self.assertEqual(state_hashes(results[0].state),state_hashes(results[1].state))
                self.assertEqual(streams[0],streams[1])
                for a,b in zip(results[0].positions,results[1].positions):
                    np.testing.assert_array_equal(a.values,b.values)
                # Atomic replacement contains the later complete state.
                updated=replace(restored,state=results[1].state,positions=results[1].positions,
                    master_key=results[1].master_key,numpy_global_state=np.random.get_state())
                save_endpoint(path,updated,target,transition,method=method,plan_hash="test",sweep=8,epoch=1)
                _,meta=load_endpoint(path,target,transition,method=method,plan_hash="test")
                self.assertEqual(meta["sweep"],8)
                with np.load(path,allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
                data["steps"][0]*=2
                with path.open("wb") as f:np.savez(f,**data)
                with self.assertRaisesRegex(ValueError,"array hash"):
                    load_endpoint(path,target,transition,method=method,plan_hash="test")

    def test_health_requires_same_factor_in_both_windows(self):
        def row(low):
            return dict(factors=[dict(index=i,acceptance=[.2 if i==low else .95,0],
                divergent=[False,False],leapfrogs=[7,0]) for i in range(2)])
        self.assertFalse(review_windows([row(0)]*25+[row(1)]*25,active_blocks=("field",))["flags"])
        flags=review_windows([row(0)]*50,active_blocks=("field",))["flags"]
        self.assertEqual(flags,[dict(factor=1,block="field",reasons=["persistent_low_acceptance"])])

if __name__=="__main__":unittest.main()
