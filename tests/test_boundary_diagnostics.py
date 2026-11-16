import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import jax
jax.config.update('jax_enable_x64', True)
import jax.numpy as jnp
import numpy as np
from bsfm.sampler.boundary_diagnostics import (
    fixed_chart_field, feature_covariance_distance, BoundaryRecorder)
from bsfm.sampler.conditional_curvature_audit import transport_field_inverse_mass
from bsfm.sampler.transition_replay_audit import energy_path
from sampler_layer6_support import fixture_system, record_result


class BoundaryAlgebraTests(unittest.TestCase):
    def test_covariance_distance_against_dense_cell_covariance(self):
        rng=np.random.default_rng(72)
        a=rng.normal(size=(17,5));b=rng.normal(size=(17,7))
        ka=a@a.T+.3*np.eye(17);kb=b@b.T+.7*np.eye(17)
        got=feature_covariance_distance(a,b,nugget_first=.3,nugget_second=.7)
        self.assertAlmostEqual(got['frobenius'],np.linalg.norm(kb-ka),places=11)
        self.assertAlmostEqual(got['relative_to_first'],np.linalg.norm(kb-ka)/np.linalg.norm(ka),places=12)

    def test_chart_prior_and_matched_kinetic_law(self):
        prior=np.array([[1.2,0],[.4,.7]])
        chart=np.array([[.8,0],[-.2,1.3]])
        q=jnp.array([.1,-.2,-.3,.15,.3,.7,-.5,.9])
        def logdensity(q):
            w=jnp.asarray(prior)@q[4:].reshape(2,2)
            return -.5*jnp.sum(q[4:]**2)-.7*jnp.sum(w**2)-.5*jnp.sum(q[:2]**2)
        full=jax.value_and_grad(logdensity)
        vg,x=fixed_chart_field(full,q,prior,chart)
        z=np.asarray(q[4:]).reshape(2,2)
        np.testing.assert_allclose(chart@x[2:].reshape(2,2),prior@z,atol=1e-14)
        expected=float(logdensity(q))+2*(np.linalg.slogdet(chart)[1]-np.linalg.slogdet(prior)[1])
        self.assertAlmostEqual(float(vg(x)[0]),expected,places=13)
        for i in range(len(x)):
            direction=np.eye(len(x))[i]*1e-5
            fd=float((vg(x+direction)[0]-vg(x-direction)[0])/2e-5)
            self.assertAlmostEqual(fd,float(vg(x)[1][i]),places=8)
        # Inherited physical kinetic law, transformed in both coordinates and momentum.
        mass=np.array([.4,.3,1.,2.,3.,4.])
        transported=transport_field_inverse_mass(mass,prior,chart)
        T=np.eye(6);T[2:,2:]=np.kron(np.linalg.solve(chart,prior),np.eye(2))
        p=np.arange(1.,7.)/10;px=np.linalg.solve(T.T,p)
        original=lambda x:full(q.at[:2].set(x[:2]).at[4:].set(x[2:]))
        original_field=lambda x:(lambda v,g:(v,jnp.r_[g[:2],g[4:]]))(*original(x))
        # Independent scalar implementation also works with the transported dense metric.
        def integrate(vg,x,p,D):
            x=jnp.asarray(x);p=jnp.asarray(p);v,g=vg(x);h0=-v+.5*p@D@p
            out=[]
            for _ in range(8):
                p=p+.005*g;x=x+.01*D@p;v,g=vg(x);p=p+.005*g
                out.append(float(-v+.5*p@D@p-h0))
            return np.array(out),np.asarray(x)
        ea,xa=integrate(original_field,np.r_[q[:2],q[4:]],p,np.diag(mass))
        eb,xb=integrate(vg,x,px,transported)
        np.testing.assert_allclose(ea,eb,atol=2e-14)
        np.testing.assert_allclose(T@xa,xb,atol=2e-14)

    def test_fixed_chart_prior_change_preserves_likelihood(self):
        old=np.array([[1.2,0],[.4,.7]]);new=np.array([[.8,0],[-.2,1.3]])
        w=np.array([[.3,.7],[-.5,.9]])
        outputs=[]
        for root in (old,new):
            q=np.r_[.1,-.2,0.,0.,np.linalg.solve(root,w).reshape(-1)]
            def ld(q):
                physical=jnp.asarray(root)@q[4:].reshape(2,2)
                return -jnp.sum((physical-.4)**2)-.5*jnp.sum(q[4:]**2)
            vg,x=fixed_chart_field(jax.value_and_grad(ld),q,root,old)
            outputs.append(float(vg(x)[0]))
        expected=-.5*(np.sum(np.linalg.solve(new,w)**2)-np.sum(np.linalg.solve(old,w)**2))
        expected-=2*(np.linalg.slogdet(new)[1]-np.linalg.slogdet(old)[1])
        self.assertAlmostEqual(outputs[1]-outputs[0],expected,places=12)


def bounded_fixture():
    # Test observation and shared-kernel identity, not long-trajectory exploration.
    with patch('bsfm.sampler.layer5.MAX_NUM_DOUBLINGS',2):
        return fixture_system()


class BoundaryReplayTests(unittest.TestCase):
    def test_observer_neutrality_and_selected_context_capture(self):
        target,state,ps,layer,tuning,scale=bounded_fixture()
        saved=np.random.get_state()
        def run(observer=None):
            np.random.seed(491)
            return layer.sweep(state,ps,tuning,eta_rng=np.random.default_rng(193),
                gauge_rng=np.random.default_rng(307),master_key=jax.random.PRNGKey(419),
                state_factor_ids=target.factor_ids,label='sweep_0001',observer=observer)
        try:
            plain=run()
            with tempfile.TemporaryDirectory() as tmp:
                recorder=BoundaryRecorder(target,0,tuning[0],Path(tmp)/'boundaries')
                events=[]
                def observe(event,state,positions,details):
                    recorder(event,state,positions,details);events.append(event)
                    # The live sampler must not share memory with the supplied snapshot.
                    state.eta.fill(np.nan);positions[0].values.fill(np.nan)
                observed=run(observe)
                self.assertEqual(record_result(plain),record_result(observed))
                self.assertEqual(events[:4],['sweep_start','after_loading','after_joint_eta','after_noise'])
                self.assertEqual(events.count('after_joint_eta'),3)
                self.assertEqual(events.count('after_px'),1)
                self.assertEqual(events.count('after_factor_transition'),len(ps))
                index=json.loads((Path(tmp)/'boundaries/index.json').read_text())
                self.assertFalse(index['authenticated_transition_replay'])
                self.assertEqual(len(index['rows']),len(events))
                with np.load(Path(tmp)/'boundaries'/index['rows'][0]['file']) as a:
                    u,ct,penalty,_=target.context(state,factor_id=target.factor_ids[0],state_factor_ids=target.factor_ids)
                    np.testing.assert_array_equal(a['u'],u)
                    np.testing.assert_array_equal(a['ct'],ct)
                    self.assertEqual(float(a['penalty']),penalty)
        finally:np.random.set_state(saved)

    def test_shared_split_audit_endpoint_matches_public_transition(self):
        target,state,ps,layer,tuning,_=bounded_fixture();p=ps[0];t=tuning[0]
        key=jax.random.PRNGKey(29)
        result=layer.split.transition(key,p,state,t,state_factor_ids=target.factor_ids)
        args,_=layer.split._inputs(key,p,state,target.factor_ids)
        tuned=layer.split._tuning(t,p.factor_id)
        ns,info,pf=layer.split._runner['audit_transition'](key,*args,
            tuned['step_size'],tuned['hyper_step_size'],tuned['inverse_mass_matrix'])
        for a,b in zip(jax.tree.leaves((ns,info)),jax.tree.leaves((result.nuts_state,result.info))):
            np.testing.assert_array_equal(a,b)
        physical=layer.split.centered._kernels['physical']
        np.testing.assert_allclose(physical(pf[2:4],pf[4:].reshape(-1,2)),
            physical(ns.position[2:4],ns.position[4:].reshape(-1,2)),atol=2e-12,rtol=2e-12)

if __name__=='__main__':unittest.main()
