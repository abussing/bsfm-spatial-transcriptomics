"""Learned stationary ranges: dense oracle, prediction and exact restart."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import jax
import jax.numpy as jnp
import numpy as np
from sampler_layer3_support import system
from bsfm.sampler.registry_rule import load_registry_rule
from bsfm.sampler.flat_control import FlatTarget, FlatTransition
from bsfm.sampler.field_target import FieldPosition
from bsfm.sampler.contracts import MU_LOG_ALPHA, VAR_LOG_ALPHA
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.run_initialization import initialize
from bsfm.sampler.run_periodic import PeriodicRunController, PeriodicReadaptationController
from bsfm.sampler.run_readaptation import parent_endpoint
from bsfm.sampler.holdout_prediction import predict_record, features
from bsfm.sampler.range_spec import validate_range_prior

PRIOR = dict(median=.18, log_sd=.25, initial=.14)


def setup(root):
    original, state, _ = system()
    rule = load_registry_rule(Path(__file__).resolve().parents[1]/
        'docs/sampler/s10-subset-smoke-20261103/L4_ell14_smoke.json',
        expected_sha256='5ebf7561ee4a72b609ebd4639d584d11360f93dd07ebf5ab4f53db75c2165168', order=4)
    target = FlatTarget(original.inputs, original.geometry, rule,
                        factor_ids=original.factor_ids, range_prior=PRIOR)
    binding = dict(kind='learned_flat_synthetic', target=target.identity)
    spec = dict(schema='bsfm.local-run.v1', run_id='production', segment_id='segment', chain_id='chain',
        factor_ids=list(target.factor_ids), seed=491, warmup_steps=20, settling_sweeps=0,
        production_sweeps=3, final_sweep=3, save_every=2, checkpoint_every=2,
        mode='exact_resume', input_sha256=digest(binding), software=dict(git_commit='0'*40,
        clean_tree=False, run_config_sha256=digest(dict(scope='learned_flat_test')),
        environment_lock_sha256='a'*64, environment_identity='synthetic_CPU_review'))
    c = PeriodicRunController(root,target,state.loading,state.eta,spec,binding,
                             authenticate=target._validate_identities)
    c.layer.split = FlatTransition(target)
    return c


class FlatRangeTests(unittest.TestCase):
    def test_dense_value_gradient_and_features(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/'run');t=c.target
            e,_=initialize(t,c.loading,c.eta,seed=491)
            self.assertEqual(e.positions[0].values.shape,(3,))
            u,ct,penalty,_=t.context(e.state,factor_id=t.factor_ids[0],state_factor_ids=t.factor_ids)
            w=jnp.asarray(t.inputs.arrays['slocs']-t.inputs.arrays['slocs'].mean(0))
            omega=jnp.asarray(t.rule.arrays['omega']);weights=jnp.asarray(t.rule.arrays['sqrt_weights'])
            def dense(q):
                phase=w@(omega*(.14/jnp.exp(q[2]))).T
                phi=jnp.concatenate([jnp.cos(phase)*weights,jnp.sin(phase)*weights],axis=1)
                a2=jnp.exp(2*q[0]);z=jax.nn.sigmoid(q[1]);n=len(u)
                cov=a2*(z*phi@phi.T+(1-z)*jnp.eye(n))
                prec=jnp.linalg.inv(cov)+jnp.diag(jnp.asarray(u))
                ll=-.5*jnp.linalg.slogdet(cov)[1]-.5*jnp.linalg.slogdet(prec)[1]
                ll+=.5*jnp.asarray(ct)@jnp.linalg.solve(prec,jnp.asarray(ct))
                return (ll+np.prod(e.state.loading.shape[:2])*q[0]-.5*a2*penalty
                    -.5*(q[0]-MU_LOG_ALPHA)**2/VAR_LOG_ALPHA+2*jnp.log(z)+2*jnp.log1p(-z)
                    -.5*((q[2]-np.log(PRIOR['median']))/PRIOR['log_sd'])**2)
            for ell in (.07,.14,.4,.8):
                p=t.range_position(t.factor_ids[0],log_alpha=e.positions[0].values[0],
                    logit_zeta=.2,log_ell_eta=np.log(ell))
                v,g,_=t.value_grad(p,e.state,state_factor_ids=t.factor_ids)
                dv,dg=jax.value_and_grad(dense)(jnp.asarray(p.values))
                np.testing.assert_allclose(v,dv,rtol=1e-10,atol=1e-10)
                np.testing.assert_allclose(g,dg,rtol=1e-9,atol=1e-9)
                wc,_,phi=t.features(p)
                np.testing.assert_array_equal(wc,np.asarray(w))
                np.testing.assert_allclose(phi,features(wc,t.rule,float(np.exp(p.values[2]))),atol=2e-14,rtol=2e-14)
            t.range_prior['median']*=2
            with self.assertRaisesRegex(ValueError,'prior changed'):t._validate_identities()

    def test_prediction_uses_each_saved_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/'run');t=c.target;e,_=initialize(t,c.loading,c.eta,seed=491)
            ranges=np.array([.08,.3]);k=len(t.factor_ids);self.assertEqual(k,2)
            train=t.inputs.arrays['slocs'];query=train[:3]+.035
            w=train-train.mean(0);wq=query-train.mean(0)
            a={n:np.array(getattr(e.state,n)) for n in ('eta','alpha','zeta','sigma2','loading')}
            a.update(ell_eta=np.exp(np.log(ranges)),positions=np.array([[0.,0.,np.log(r)] for r in ranges]),
                     W_cell=np.stack([w]*k))
            types=np.zeros(len(query),dtype=np.int64)
            mean,var=predict_record(t,a,None,query,types,rng=np.random.default_rng(7))
            em=np.zeros_like(mean);ev=np.broadcast_to(a['sigma2'][:,None],var.shape).copy()
            for i,r in enumerate(ranges):
                pt=features(w,t.rule,r);pq=features(wq,t.rule,r)
                sv=a['alpha'][i]**2*a['zeta'][i];nv=a['alpha'][i]**2*(1-a['zeta'][i])
                cov=sv*pt@pt.T+nv*np.eye(len(train));cross=sv*pq@pt.T
                fm=cross@np.linalg.solve(cov,a['eta'][i])
                fv=np.diag(sv*pq@pq.T+nv*np.eye(len(query))-cross@np.linalg.solve(cov,cross.T))
                lam=a['loading'][0,:,i];em+=lam[:,None]*fm;ev+=lam[:,None]**2*fv
            np.testing.assert_allclose(mean,em,atol=1e-10,rtol=1e-10)
            np.testing.assert_allclose(var,ev,atol=1e-10,rtol=1e-10)
            a['ell_eta'][0]=.14
            with self.assertRaisesRegex(ValueError,'disagree'):predict_record(t,a,None,query,types,rng=np.random.default_rng(7))

    def test_periodic_restart_and_saved_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);whole=setup(root/'whole');whole.run()
            resumed=setup(root/'resumed');resumed.run(stop_after=1)
            class Stop(BaseException): pass
            def interrupt(stage):
                if stage=='before_boundary_publish':raise Stop()
            with self.assertRaises(Stop):resumed.run(fault=interrupt)
            resumed=setup(root/'resumed');result=resumed.run()
            with patch.object(resumed.layer,'sweep',side_effect=AssertionError('replayed')):
                self.assertEqual(resumed.run(),result)
            left=whole.store.segment/'boundaries';right=resumed.store.segment/'boundaries'
            self.assertEqual(len(list(left.glob('*/record.npz'))),3)
            for l in sorted(left.glob('*/record.npz')):
                r=right/l.parent.name/l.name
                with np.load(l) as x,np.load(r) as y:
                    for key in x.files:
                        if key!='metadata':np.testing.assert_array_equal(x[key],y[key])
                    self.assertEqual(x['positions'].shape,(2,3))
                    np.testing.assert_array_equal(x['ell_eta'],np.exp(x['positions'][:,2]))
                    self.assertFalse(np.array_equal(x['ell_eta'],np.full(2,.14)))
            # Full checkpoint metadata includes stream states; timing diagnostics differ.
            for l in sorted(left.glob('*/checkpoint.npz')):
                with np.load(l) as x,np.load(right/l.parent.name/l.name) as y:
                    for key in x.files:
                        if key!='metadata':np.testing.assert_array_equal(x[key],y[key])
                    self.assertEqual(json.loads(str(x['metadata']))['rng'],json.loads(str(y['metadata']))['rng'])
            _,parent_binding=parent_endpoint(resumed)
            binding=dict(resumed.store.input_receipt,readaptation_parent=parent_binding)
            spec=copy.deepcopy(resumed.spec)
            spec.update(run_id='retuned',production_sweeps=1,final_sweep=1,input_sha256=digest(binding))
            child=PeriodicReadaptationController(root/'retuned',resumed.target,resumed.loading,resumed.eta,
                spec,binding,authenticate=resumed.authenticate,parent=resumed)
            child.layer.split=FlatTransition(resumed.target)
            with patch('bsfm.sampler.run_controller.initialize',side_effect=AssertionError('reinitialized')):
                child.run()

    def test_prior_requires_explicit_valid_values(self):
        for prior in ({},dict(PRIOR,log_sd=0),dict(PRIOR,log_sd=1e300),dict(PRIOR,log_sd=1e-300),
                      dict(PRIOR,median=float('nan')),dict(PRIOR,initial=True)):
            with self.assertRaises(ValueError):validate_range_prior(prior)


if __name__=='__main__':unittest.main()
