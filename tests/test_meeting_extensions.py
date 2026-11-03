"""Bounded synthetic regression of explicit retuning and identity-coordinate control."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import jax
import jax.numpy as jnp
import numpy as np
from sampler_layer3_support import system
from smoke_rule import load_smoke_rule
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.contracts import MU_LOG_ALPHA, VAR_LOG_ALPHA
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.flat_control import FlatTarget, FlatTransition
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_readaptation import ReadaptationController, parent_endpoint
from bsfm.sampler.run_genesis import load_genesis
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.run_storage import read_json


def setup(root, model):
    original, state, _ = system()
    cls = FlatTarget if model == 'flat' else DirectWTarget
    target = cls(original.inputs, original.geometry, load_smoke_rule(), factor_ids=original.factor_ids)
    binding = dict(kind='synthetic_meeting_extensions', target=target.identity)
    spec = dict(schema='bsfm.local-run.v1', run_id='bridge', segment_id='segment', chain_id='chain',
        factor_ids=list(target.factor_ids), seed=491, warmup_steps=20, settling_sweeps=0,
        production_sweeps=1, final_sweep=1, save_every=1, checkpoint_every=1,
        mode='exact_resume', input_sha256=digest(binding), software=dict(git_commit='9c584353e74043e323ca327ff1764f9d094980d5',
        clean_tree=False, run_config_sha256=digest(dict(scope='synthetic_extensions')),
        environment_lock_sha256='a'*64, environment_identity='synthetic_CPU_review'))
    c = RunController(root, target, state.loading, state.eta, spec, binding, authenticate=target._validate_identities)
    if model == 'flat': c.layer.split = FlatTransition(target)
    return c


class MeetingExtensions(unittest.TestCase):
    def test_conditional_warp_preserves_observed_active_field(self):
        from bsfm.sampler.holdout_prediction import conditional_warp
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/'deep','deep')
            e,_=initialize(c.target,c.loading,c.eta,seed=491)
            w,wa,_=c.target.features(e.positions[0])
            query=conditional_warp(c.target.geometry,wa,0.,.31622776601683794,
                c.target.geometry.arrays['projector'],np.random.default_rng(61))
            np.testing.assert_allclose(query,w,rtol=2e-8,atol=2e-10)

    def test_prediction_matches_dense_gaussian(self):
        from bsfm.sampler.holdout_prediction import conditional_factor
        rng=np.random.default_rng(61)
        train=rng.normal(size=(9,5)); query=rng.normal(size=(4,5)); eta=rng.normal(size=9)
        alpha,zeta=.8,.6; sv=alpha**2*zeta; nv=alpha**2*(1-zeta)
        covariance=sv*(train@train.T)+nv*np.eye(9)
        cross=sv*query@train.T
        expected=cross@np.linalg.solve(covariance,eta)
        variance=np.diag(sv*query@query.T+nv*np.eye(4)-cross@np.linalg.solve(covariance,cross.T))
        mean,actual=conditional_factor(train,eta,query,alpha,zeta)
        np.testing.assert_allclose(mean,expected,rtol=1e-12,atol=1e-12)
        np.testing.assert_allclose(actual,variance,rtol=1e-12,atol=1e-12)

    def test_flat_dense_target_and_gradient(self):
        with tempfile.TemporaryDirectory() as tmp:
            c = setup(Path(tmp)/'flat', 'flat')
            e, _ = initialize(c.target, c.loading, c.eta, seed=491)
            p = e.positions[0]
            u, ct, penalty, _ = c.target.context(e.state, factor_id=p.factor_id, state_factor_ids=c.target.factor_ids)
            phi = jnp.asarray(c.target.features(p)[2]); n = len(u)
            def dense(q):
                a2=jnp.exp(2*q[0]); z=jax.nn.sigmoid(q[1])
                covariance=a2*(z*phi@phi.T+(1-z)*jnp.eye(n))
                precision=jnp.linalg.inv(covariance)+jnp.diag(jnp.asarray(u))
                value=-.5*jnp.linalg.slogdet(covariance)[1]-.5*jnp.linalg.slogdet(precision)[1]
                value+=.5*jnp.asarray(ct)@jnp.linalg.solve(precision,jnp.asarray(ct))
                dim=np.prod(e.state.loading.shape[:2])
                return value+dim*q[0]-.5*a2*penalty-.5*(q[0]-MU_LOG_ALPHA)**2/VAR_LOG_ALPHA+2*jnp.log(z)+2*jnp.log1p(-z)
            value, grad, _=c.target.value_grad(p,e.state,state_factor_ids=c.target.factor_ids)
            dv,dg=jax.value_and_grad(dense)(jnp.asarray(p.values[:2]))
            np.testing.assert_allclose(value,dv,rtol=1e-10,atol=1e-10)
            np.testing.assert_allclose(grad[:2],dg,rtol=1e-10,atol=1e-10)
            self.assertTrue(np.all(grad[2:]==0))

    def test_both_models_child_retuning_and_no_replay(self):
        for model in ('flat','deep'):
            with self.subTest(model=model), tempfile.TemporaryDirectory() as tmp:
                parent=setup(Path(tmp)/'bridge',model)
                parent.run()
                endpoint, binding=parent_endpoint(parent)
                inventory={str(p.relative_to(parent.store.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in parent.store.root.rglob('*') if p.is_file()}
                receipt=dict(parent.store.input_receipt,readaptation_parent=binding)
                spec=copy.deepcopy(parent.spec);spec['run_id']='production';spec['input_sha256']=digest(receipt)
                spec['software']['run_config_sha256']=digest({k:v for k,v in spec.items() if k!='software'})
                child=ReadaptationController(Path(tmp)/'production',parent.target,parent.loading,parent.eta,spec,receipt,
                    authenticate=parent.authenticate,parent=parent)
                if model=='flat':child.layer.split=FlatTransition(parent.target)
                with patch('bsfm.sampler.run_controller.initialize',side_effect=AssertionError('Child reinitialized')):
                    child.run(stop_after=0)
                    genesis,_=load_genesis(child.store.segment/'genesis/endpoint.npz',child.target,child.cp)
                    self.assertEqual(genesis.evidence['initialization']['parent'],binding)
                    expected=jax.random.split(endpoint.master_key,len(parent.target.factor_ids)+1)[0]
                    np.testing.assert_array_equal(genesis.master_key,expected)
                    if model=='flat':
                        for p in genesis.positions:np.testing.assert_array_equal(p.values[2:],parent.target.fixed_tail)
                    result=child.run()
                    with patch.object(child.layer,'sweep',side_effect=AssertionError('Replay')):
                        self.assertEqual(child.run(),result)
                for rel,h in inventory.items():
                    self.assertEqual(hashlib.sha256((parent.store.root/rel).read_bytes()).hexdigest(),h)
                changed=copy.deepcopy(receipt);changed['readaptation_parent']['head']='0'*64
                bad=copy.deepcopy(spec);bad['input_sha256']=digest(changed)
                with self.assertRaises(ValueError):
                    ReadaptationController(Path(tmp)/'bad',parent.target,parent.loading,parent.eta,bad,changed,
                        authenticate=parent.authenticate,parent=parent)


if __name__=='__main__':unittest.main()
