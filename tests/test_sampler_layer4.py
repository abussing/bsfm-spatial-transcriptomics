"""Exact saved references and independent conditional-Gaussian Layer-4 checks."""
import ast
import copy
import csv
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import jax
import jax.numpy as jnp
import numpy as np
from threadpoolctl import threadpool_limits
from bsfm.sampler import joint_eta_kernels as je
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.layer4 import (CenteredHyperTarget, JointEtaConditional,
    MAXIMUM_PCG_ITERATIONS, POSTERIOR_RMS_TOLERANCE, state_hashes)
from sampler_layer4_support import (ROOT, system, positions, evaluate, small_joint,
    dense_fixed_w, dense_eta, dense_perturbation)
from sampler_provenance import body_ast_sha256

FIXTURE=json.loads((ROOT/'tests/fixtures/sampler_layer4.json').read_text())


class Layer4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads=threadpool_limits(limits=1);cls.threads.__enter__()
        cls.target,cls.state,cls.pos=system(12)
        cls.positions=positions(cls.target,cls.state,cls.pos)
        cls.centered=CenteredHyperTarget(cls.target)
        cls.field=cls.centered.freeze(cls.pos,cls.state,state_factor_ids=cls.target.factor_ids)
        cls.joint=JointEtaConditional(cls.target)

    @classmethod
    def tearDownClass(cls):cls.threads.__exit__(None,None,None)

    def test_saved_historical_values_draws_diagnostics_rng_exact(self):
        for case in FIXTURE['cases']:
            with self.subTest(seed=case['seed']):self.assertEqual(evaluate(case['seed']),case['expected'])

    def test_provenance_all_twelve_bodies_and_file_hashes(self):
        with (ROOT/'docs/sampler/LAYER4_SOURCE_MAP.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),12)
        sources={r['path']:r for r in FIXTURE['sources']}
        for r in rows:
            self.assertEqual(r['source_sha256'],sources[r['source_path']]['sha256'])
            b=(ROOT/r['port_path']).read_bytes();self.assertEqual(hashlib.sha256(b).hexdigest(),r['port_file_sha256'])
            n=next(n for n in ast.parse(b).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name==r['port_function'])
            self.assertEqual([n.lineno,n.end_lineno],[int(r['port_start']),int(r['port_end'])])
            self.assertEqual(body_ast_sha256(n),r['source_body_ast_sha256'])
            self.assertEqual(body_ast_sha256(n),r['port_body_ast_sha256'])

    def test_centered_independent_full_precision_density_and_gradient(self):
        for xb in (np.array([-.2,.1]),np.array([.15,-.08])):
            v,g,_=self.centered.value_grad(xb,self.field,self.state,state_factor_ids=self.target.factor_ids)
            ref,grad=jax.value_and_grad(lambda x:dense_fixed_w(self.target.geometry,x,jnp.asarray(self.field.values)))(jnp.asarray(xb))
            self.assertLessEqual(abs(v-float(ref))/max(1,abs(float(ref))),2e-12)
            self.assertLessEqual(np.linalg.norm(g-grad)/max(1,np.linalg.norm(grad)),2e-10)

    def test_two_columns_determinant_and_explicit_priors(self):
        zero=np.zeros_like(self.field.values)
        field=replace(self.field,values=zero,values_sha256=logical_hash(zero))
        for xb in (np.array([0.,0.]),np.array([.25,-.18])):
            v,_,_=self.centered.value_grad(xb,field,self.state,state_factor_ids=self.target.factor_ids)
            cov=np.asarray(self.target.geometry.geometry(xb[0])[2])*np.exp(2*xb.sum())/10
            logdet=np.linalg.slogdet(cov)[1]
            priors=-.5*(xb[0]/.5)**2-.5*(xb[1]/.3)**2
            self.assertAlmostEqual(v,-logdet+priors,places=11)
            self.assertGreater(abs(v-(-.5*logdet+priors)),.01)

    def test_centered_ignores_likelihood_loading_and_eta(self):
        s=copy.deepcopy(self.state);s.loading*=1.7;s.eta+=4;s.sigma2*=.2
        xb=np.array([.1,-.2])
        with patch.object(self.target,'value_grad',side_effect=AssertionError('likelihood called')):
            a=self.centered.value_grad(xb,self.field,self.state,state_factor_ids=self.target.factor_ids)
            b=self.centered.value_grad(xb,self.field,s,state_factor_ids=self.target.factor_ids)
        self.assertEqual(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1])
        self.assertNotEqual(a[2]['state_array_hashes'],b[2]['state_array_hashes'])

    def test_rewhitening_exact_source_and_physical_preservation(self):
        xb=self.pos.values[2:4]+np.array([.07,-.04])
        z,record=self.centered.rewhiten(xb,self.field,self.state,state_factor_ids=self.target.factor_ids)
        np.testing.assert_array_equal(z,FIXTURE['cases'][0]['expected']['rewhitened'])
        restored=self.centered._kernels['physical'](jnp.asarray(xb),jnp.asarray(z))
        np.testing.assert_allclose(restored,self.field.values,rtol=0,atol=2e-8)
        self.assertLessEqual(record['max_absolute_error'],2e-8)

    def test_rewhitening_failure_is_fatal(self):
        with patch.dict(self.centered._kernels,whiten=lambda xb,w:jnp.full_like(w,jnp.nan)):
            with self.assertRaisesRegex(RuntimeError,'rewhitening'):
                self.centered.rewhiten(np.zeros(2),self.field,self.state,state_factor_ids=self.target.factor_ids)

    def test_centered_malformed_and_nonfinite_parameters(self):
        for xb in (np.array([np.nan,0.]),np.array([0.,np.inf]),np.array([1000.,0.]),
                   np.zeros(3),np.zeros(2,dtype=np.float32),[0.,0.]):
            with self.subTest(xb=xb),self.assertRaises(ValueError):
                self.centered.value_grad(xb,self.field,self.state,state_factor_ids=self.target.factor_ids)

    def test_centered_mutated_field_and_wrong_identity_rejected(self):
        for field in (replace(self.field,target_identity='other'),replace(self.field,factor_id='other'),
                      replace(self.field,values=self.field.values+1),replace(self.field,values=np.full_like(self.field.values,np.nan))):
            with self.assertRaises(ValueError):self.centered.value_grad(np.zeros(2),field,self.state,state_factor_ids=self.target.factor_ids)

    def test_state_and_factor_order_binding(self):
        s=replace(self.state,input_identity_json='different')
        for state,ids in ((s,self.target.factor_ids),(self.state,self.target.factor_ids[::-1])):
            with self.assertRaises(ValueError):self.centered.value_grad(np.zeros(2),self.field,state,state_factor_ids=ids)
            with self.assertRaises(ValueError):self.joint.draw(self.positions,state,np.random.default_rng(1),state_factor_ids=ids)

    def test_joint_public_boundary_exact_and_immutable(self):
        before=state_hashes(self.state);y=logical_hash(self.target.inputs.arrays['Y']);rng=np.random.default_rng(901)
        eta,beta,d,record=self.joint.draw(self.positions,self.state,rng,state_factor_ids=self.target.factor_ids)
        ref=FIXTURE['cases'][0]['expected']['canonical']
        np.testing.assert_array_equal(eta,ref['eta']);self.assertEqual(logical_hash(beta),ref['beta_sha256'])
        self.assertEqual(asdict(d),ref['diagnostics']);self.assertEqual(rng.bit_generator.state,ref['rng_after'])
        self.assertEqual(record['rng_before'],ref['rng_before']);self.assertEqual(record['rng_after'],ref['rng_after'])
        self.assertEqual(before,state_hashes(self.state));self.assertEqual(y,logical_hash(self.target.inputs.arrays['Y']))

    def test_joint_positions_and_state_parameters_must_agree(self):
        rng=np.random.default_rng(4);before=copy.deepcopy(rng.bit_generator.state)
        for ps in (self.positions[::-1],self.positions[:1],list(self.positions),(self.pos,self.positions[1])):
            with self.assertRaises(ValueError):self.joint.draw(ps,self.state,rng,state_factor_ids=self.target.factor_ids)
        self.assertEqual(before,rng.bit_generator.state)

    def test_rejected_state_does_not_mutate_rng_or_arrays(self):
        state=copy.deepcopy(self.state);state.sigma2[0]=np.nan
        original=state.sigma2.copy();rng=np.random.default_rng(12);before=copy.deepcopy(rng.bit_generator.state)
        with self.assertRaises(ValueError):self.joint.draw(self.positions,state,rng,state_factor_ids=self.target.factor_ids)
        self.assertEqual(before,rng.bit_generator.state);np.testing.assert_array_equal(state.sigma2,original)

    def test_joint_explicit_numpy_rng_not_jax_key(self):
        for rng in (123,jax.random.PRNGKey(123),None):
            with self.assertRaises(ValueError):self.joint.draw(self.positions,self.state,rng,state_factor_ids=self.target.factor_ids)

    def test_changed_rule_or_geometry_identity_rejected(self):
        t,s,p=system(19);joint=JointEtaConditional(t);ps=positions(t,s,p)
        t.identity=t.identity+' '
        with self.assertRaises(ValueError):joint.draw(ps,s,np.random.default_rng(1),state_factor_ids=t.factor_ids)

    def test_cell_statistics_independent_observation_space(self):
        kw=small_joint();_,_,ref=dense_perturbation(kw)
        np.testing.assert_allclose(ref['h'],ref['h_dense'],rtol=2e-12,atol=2e-12)
        np.testing.assert_allclose(ref['s'],ref['s_dense'],rtol=2e-12,atol=2e-12)

    def test_precision_and_block_preconditioner_independent_dense(self):
        kw=small_joint();_,_,ref=dense_perturbation(kw);f=np.sqrt(kw['zeta'])[:,None,None]*kw['features']
        x=np.arange(8,dtype=float).reshape(2,4)/7
        np.testing.assert_allclose(je._precision_matvec(f,ref['h'],x).reshape(-1),ref['q']@x.reshape(-1),rtol=2e-12,atol=2e-12)
        chol=np.asarray(je._block_preconditioner_cholesky(f,ref['h']))
        for k in range(2):np.testing.assert_allclose(chol[k]@chol[k].T,ref['q'][k*4:(k+1)*4,k*4:(k+1)*4],rtol=2e-12,atol=2e-12)
        solved=np.asarray(je._preconditioner_solve(chol,x))
        for k in range(2):np.testing.assert_allclose(solved[k],np.linalg.solve(chol[k]@chol[k].T,x[k]),rtol=2e-12,atol=2e-12)

    def test_draw_matches_dense_algebra_identical_innovations(self):
        for seed in (91,116):
            kw=small_joint(seed);rng=np.random.default_rng(901)
            eta,beta,d=je.sample_joint_eta_pcg(rng,**kw)
            expected,betaref,ref=dense_perturbation(kw)
            # PCG promises a posterior-metric bound, not 2e-12 elementwise
            # equality to a dense solve. Test that promised metric directly.
            error=(beta-betaref).reshape(-1)
            self.assertLessEqual(np.sqrt(error@ref['q']@error/error.size),
                                 d.posterior_mahalanobis_RMS_error_upper_bound+2e-12)
            # The conditional nugget uses the same innovations. Its mean shifts
            # linearly with the bounded beta solve error; verify that propagation.
            np.testing.assert_allclose((eta-expected).reshape(-1),ref['eta_beta_map']@error,
                                       rtol=2e-12,atol=2e-12)
            eta_allowance=np.linalg.norm(ref['eta_beta_map'],2)*np.sqrt(error.size)*d.posterior_mahalanobis_RMS_error_upper_bound
            self.assertLessEqual(np.linalg.norm(eta-expected),eta_allowance+2e-12)
            self.assertEqual(rng.bit_generator.state,ref['rng_after'])

    def test_innovation_map_mean_covariance_match_dense_eta_posterior(self):
        kw=small_joint();k,n,r=kw['features'].shape;dim=k*r+2*n*k
        def decode(z):return z[:k*r].reshape(k,r),z[k*r:k*r+n*k].reshape(n,k),z[k*r+n*k:].reshape(n,k)
        mean=dense_perturbation(kw,innovations=decode(np.zeros(dim)))[0]
        columns=[]
        for j in range(dim):
            z=np.zeros(dim);z[j]=1
            columns.append((dense_perturbation(kw,innovations=decode(z))[0]-mean).reshape(-1))
        transform=np.column_stack(columns);densemean,densecov=dense_eta(kw)
        np.testing.assert_allclose(mean,densemean,rtol=2e-12,atol=2e-12)
        np.testing.assert_allclose(transform@transform.T,densecov,rtol=2e-12,atol=2e-12)

    def test_posterior_metric_bound_independent_true_solution(self):
        kw=small_joint();_,_,ref=dense_perturbation(kw)
        f=np.sqrt(kw['zeta'])[:,None,None]*kw['features'];h=ref['h']
        noise,_=je._precision_noise(np.random.default_rng(901),f,h)
        rhs=np.einsum('knr,nk->kr',f,ref['s'],optimize=True)+noise
        chol=je._block_preconditioner_cholesky(f,h)
        it,beta,residual,_,_,_=je._pcg(f,h,chol,rhs,jnp.asarray(1e-10),maximum_iterations=80)
        bound=np.linalg.norm(residual)/np.sqrt(rhs.size)
        error=np.asarray(beta).reshape(-1)-np.linalg.solve(ref['q'],rhs.reshape(-1))
        true_rms=np.sqrt(error@ref['q']@error/rhs.size)
        # Account for independent dense-solve roundoff, not a changed PCG threshold.
        self.assertLessEqual(true_rms,bound+2e-12)
        _,_,d=je.sample_joint_eta_pcg(np.random.default_rng(901),**kw)
        self.assertEqual(d.posterior_mahalanobis_RMS_error_upper_bound,float(bound))
        self.assertLessEqual(bound,1e-10);self.assertEqual(d.iterations,int(it))
        self.assertGreaterEqual(np.linalg.eigvalsh(ref['q']).min(),1-2e-12)

    def test_nonconvergence_fatal_no_partial_state_update(self):
        original=je._pcg;before=state_hashes(self.state)
        def limited(*args,**kwargs):kwargs['maximum_iterations']=0;return original(*args,**kwargs)
        with patch.object(je,'_pcg',limited):
            with self.assertRaisesRegex(RuntimeError,'joint eta PCG failed'):
                self.joint.draw(self.positions,self.state,np.random.default_rng(901),state_factor_ids=self.target.factor_ids)
        self.assertEqual(before,state_hashes(self.state))
        self.assertEqual(MAXIMUM_PCG_ITERATIONS,80);self.assertEqual(POSTERIOR_RMS_TOLERANCE,1e-10)

    def test_non_psd_coupling_fails_historical_threshold(self):
        f=np.ones((2,3,4));h=np.broadcast_to(-np.eye(2),(3,2,2))
        with self.assertRaisesRegex(RuntimeError,'not PSD'):je._precision_noise(np.random.default_rng(2),f,h)

    def test_same_process_determinism(self):
        self.assertEqual(evaluate(12),evaluate(12))

    def test_fresh_process_determinism(self):
        code='import json; from threadpoolctl import threadpool_limits; from sampler_layer4_support import evaluate; t=threadpool_limits(limits=1); print(json.dumps(evaluate(12),sort_keys=True))'
        env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')])
        output=subprocess.check_output([sys.executable,'-B','-c',code],env=env,text=True)
        self.assertEqual(json.loads(output),FIXTURE['cases'][0]['expected'])


if __name__=='__main__':unittest.main()
