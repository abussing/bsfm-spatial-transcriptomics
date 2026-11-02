"""Exact selected-source regressions and independent cell-space Gaussian checks."""
import ast
import copy
import csv
from dataclasses import replace
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
from bsfm.sampler import contracts,warp
from bsfm.sampler.rule import FrozenRule,load_rule,REGISTRY,REGISTRY_SHA256
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.factor_statistics import sample_single_eta
from bsfm.sampler.finite_features import make_feature_kernel
from sampler_layer3_support import ROOT,system,evaluate,dense_target

FIXTURE=json.loads((ROOT/'tests/fixtures/sampler_layer3.json').read_text(encoding='utf-8'))


class TargetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.limit=threadpool_limits(limits=1);cls.limit.__enter__()
        cls.target,cls.state,cls.pos=system()
        cls.outputs=[evaluate(*system(c['seed'])) for c in FIXTURE['cases']]
    @classmethod
    def tearDownClass(cls):cls.limit.__exit__(None,None,None)

    def test_exact_original_target_values_and_all_gradients(self):
        for got,c in zip(self.outputs,FIXTURE['cases']):
            for k in ('value','gradient','reference_value','reference_gradient'):
                self.assertEqual(got[k],c['expected'][k])

    def test_exact_original_feature_arrays_and_physical_coordinates(self):
        for got,c in zip(self.outputs,FIXTURE['cases']):
            for k in ('features_sha256','features_shape','W','W_active'):
                self.assertEqual(got[k],c['expected'][k])

    def test_exact_original_statistics(self):
        for got,c in zip(self.outputs,FIXTURE['cases']):
            for k in ('u','ct','penalty'):self.assertEqual(got[k],c['expected'][k])

    def test_exact_original_eta_and_rng(self):
        for got,c in zip(self.outputs,FIXTURE['cases']):
            for k in ('eta','rng_after'):self.assertEqual(got[k],c['expected'][k])
        rng=np.random.default_rng(831)
        draw,_=self.target.draw_eta(self.pos,self.state,rng,state_factor_ids=self.target.factor_ids)
        self.assertEqual(draw.tolist(),FIXTURE['cases'][0]['expected']['eta'])
        self.assertEqual(rng.bit_generator.state,FIXTURE['cases'][0]['expected']['rng_after'])

    def test_public_target_equals_original_and_input_state_unchanged(self):
        y=self.target.inputs.arrays['Y'].copy();before=copy.deepcopy(self.state)
        value,gradient,_=self.target.value_grad(self.pos,self.state,state_factor_ids=self.target.factor_ids)
        self.assertEqual(value,FIXTURE['cases'][0]['expected']['value'])
        self.assertEqual(gradient.tolist(),FIXTURE['cases'][0]['expected']['gradient'])
        np.testing.assert_array_equal(y,self.target.inputs.arrays['Y'])
        for key in ('loading','eta','sigma2','phi','delta','tau','alpha','zeta'):
            np.testing.assert_array_equal(getattr(before,key),getattr(self.state,key))

    def test_rule_registry_and_weight_tolerances(self):
        self.assertEqual(hashlib.sha256(REGISTRY.read_bytes()).hexdigest(),REGISTRY_SHA256)
        r=self.target.rule;identity=json.loads(r.identity_json)
        self.assertEqual(identity['ell_eta'],.14);self.assertEqual(identity['feature_columns'],1024)
        self.assertEqual(r.arrays['omega'].shape,(512,2));self.assertTrue(identity['x64_required'])
        self.assertLessEqual(abs(r.arrays['weights'].sum()-1),2e-14)

    def test_recorded_provenance_and_selected_branch_boundary(self):
        def functions(node,prefix=''):
            result={}
            for x in node.body:
                if isinstance(x,(ast.FunctionDef,ast.ClassDef)):
                    name=prefix+x.name;result[name]=x;result.update(functions(x,name+'.'))
            return result
        with (ROOT/'docs/sampler/LAYER3_SOURCE_MAP.csv').open(encoding='utf-8',newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),22)
        source_records={s['path']:s for s in FIXTURE['sources']}
        for row in rows:
            self.assertEqual(row['source_sha256'],source_records[row['source_path']]['sha256'])
            raw=(ROOT/row['port_path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['port_file_sha256'])
            node=functions(ast.parse(raw))[row['port_function']]
            self.assertEqual([node.lineno,node.end_lineno],[int(row['port_start']),int(row['port_end'])])
            body=ast.dump(ast.Module(body=node.body,type_ignores=[]),include_attributes=False)
            self.assertEqual(hashlib.sha256(body.encode()).hexdigest(),row['port_body_ast_sha256'])
            if row['body_ast_exact']=='True':self.assertEqual(row['source_body_ast_sha256'],row['port_body_ast_sha256'])
        kernels=(ROOT/'src/bsfm/sampler/field_kernels.py').read_text(encoding='utf-8')
        for rejected in ('containment','soft_eta','eta_floor','fixed_physical','blackjax','LI_'):
            self.assertNotIn(rejected,kernels)
        identity=json.loads(self.target.identity)
        self.assertEqual(identity['priors']['log_r_variance'],.3**2)
        self.assertEqual(identity['priors']['zeta_beta'],[2.,2.])

    def test_explicit_feature_order_and_finite_feature_covariance(self):
        w,_,f=self.target.features(self.pos);r=self.target.rule.arrays
        phase=jnp.asarray(w)@jnp.asarray(r['omega']).T
        expected=jnp.concatenate((jnp.cos(phase)*r['sqrt_weights'],jnp.sin(phase)*r['sqrt_weights']),axis=1)
        np.testing.assert_array_equal(f,expected)
        self.assertEqual(f.shape,(3,1024))
        kernel=(np.cos((w[:,None,:]-w[None,:,:])@r['omega'].T)*r['weights']).sum(-1)
        np.testing.assert_allclose(f@f.T,kernel,rtol=2e-12,atol=2e-12)

    def test_statistics_independent_gene_cell_sums(self):
        t,s,p=self.target,self.state,self.pos;u,ct,penalty,_=t.context(s,factor_id=p.factor_id,state_factor_ids=t.factor_ids)
        k=1;expected_u=[];expected_ct=[]
        for i,c in enumerate(t.inputs.arrays['cell_id']):
            residual=t.inputs.arrays['Y'][:,i]-sum(s.loading[c,:,j]*s.eta[j,i] for j in range(2) if j!=k)
            expected_u.append(sum(s.loading[c,g,k]**2/s.sigma2[g] for g in range(2)))
            expected_ct.append(sum(s.loading[c,g,k]*residual[g]/s.sigma2[g] for g in range(2)))
        np.testing.assert_allclose(u,expected_u,rtol=2e-12,atol=2e-12)
        np.testing.assert_allclose(ct,expected_ct,rtol=2e-12,atol=2e-12)
        inv=np.linalg.inv(.8*np.eye(3)+.2*np.ones((3,3)))
        q=np.array([s.loading[:,g,k]@inv@s.loading[:,g,k] for g in range(2)])
        self.assertLess(abs(penalty-s.tau[k]*np.sum(s.phi[:,k]*q)),2e-12)

    def test_dense_Gaussian_integration_value_and_gradient(self):
        t,s,p=self.target,self.state,self.pos;x=jnp.asarray(p.values)
        value,gradient,_=t.value_grad(p,s,state_factor_ids=t.factor_ids)
        dense,dense_grad=jax.value_and_grad(lambda x:dense_target(t,s,p,x))(x)
        self.assertLessEqual(abs(value-float(dense))/max(1,abs(float(dense))),2e-12)
        self.assertLessEqual(np.linalg.norm(gradient-np.asarray(dense_grad))/max(1,np.linalg.norm(dense_grad)),2e-10)

    def test_single_eta_posterior_moments_and_innovation_map(self):
        t,s,p=self.target,self.state,self.pos
        f=t.features(p)[2];u,ct,_,_=t.context(s,factor_id=p.factor_id,state_factor_ids=t.factor_ids)
        alpha=np.exp(p.values[0]);zeta=float(jax.nn.sigmoid(p.values[1]));a=alpha**2*zeta;b=alpha**2*(1-zeta)
        den=1+b*u;h=np.eye(1024)+a*f.T@((u/den)[:,None]*f);l=np.linalg.cholesky(h)
        # Independent cell covariance calculation.
        c=a*f@f.T+b*np.eye(len(u));cov=np.linalg.inv(np.linalg.inv(c)+np.diag(u));mean=cov@ct
        # Moments implied by the selected two-independent-normal draw algorithm.
        meanbeta=np.linalg.solve(h,np.sqrt(a)*f.T@(ct/den))
        algorithm_mean=(np.sqrt(a)*f@meanbeta+b*ct)/den
        fden=f/den[:,None]
        algorithm_cov=a*fden@np.linalg.solve(h,fden.T)+np.diag(b/den)
        np.testing.assert_allclose(algorithm_mean,mean,rtol=2e-12,atol=2e-12)
        np.testing.assert_allclose(algorithm_cov,cov,rtol=2e-12,atol=2e-12)
        rng=np.random.default_rng(831);normal_beta=rng.standard_normal(1024);normal_cell=rng.standard_normal(len(u))
        innovation=mean+np.sqrt(a)*fden@np.linalg.solve(l.T,normal_beta)+np.sqrt(b/den)*normal_cell
        np.testing.assert_allclose(innovation,FIXTURE['cases'][0]['expected']['eta'],rtol=2e-12,atol=2e-12)

    def test_direct_W_no_identity_and_coupled_warp(self):
        t,p=self.target,self.pos;z=np.zeros((len(t.geometry.arrays['active_indices']),2))
        zero=t.position(p.factor_id,log_alpha=p.values[0],logit_zeta=p.values[1],log_ell=p.values[2],log_r=p.values[3],zW=z)
        np.testing.assert_array_equal(t.features(zero)[0],np.zeros((3,2)))
        np.testing.assert_allclose(t.features(p)[0],t.geometry.physical(p.values[2],p.values[3],p.values[4:].reshape(-1,2))['W_cell'],rtol=2e-12,atol=2e-12)

    def test_exact_SE_is_diagnostic_only(self):
        t,s,p=self.target,self.state,self.pos;w,_,f=t.features(p)
        value,gradient,_=t.value_grad(p,s,state_factor_ids=t.factor_ids)
        def diagnostic(ell):return np.exp(-2*np.sum((w[:,None,:]-w[None,:,:])**2,axis=2)/ell**2)
        self.assertFalse(np.array_equal(diagnostic(.14),diagnostic(.31)))
        changed_diagnostic=diagnostic(.31)*0+7
        self.assertFalse(np.array_equal(f@f.T,changed_diagnostic))
        other,g,_=t.value_grad(p,s,state_factor_ids=t.factor_ids)
        self.assertEqual(value,other);np.testing.assert_array_equal(gradient,g)

    def test_current_state_rebuild_no_stale_context(self):
        t,s,p=self.target,self.state,self.pos
        original=t.value_grad(p,s,state_factor_ids=t.factor_ids)
        changed=copy.deepcopy(s);changed.eta[0,0]+=.7;changed.sigma2[0]*=1.3;changed.phi[0,1]*=1.4
        got=t.value_grad(p,changed,state_factor_ids=t.factor_ids)
        fresh=DirectWTarget(t.inputs,t.geometry,t.rule,factor_ids=t.factor_ids).value_grad(p,changed,state_factor_ids=t.factor_ids)
        self.assertNotEqual(original[0],got[0]);self.assertNotEqual(original[2],got[2])
        self.assertEqual(got[0],fresh[0]);np.testing.assert_array_equal(got[1],fresh[1])

    def test_repeated_and_fresh_process_exact(self):
        self.assertEqual(evaluate(*system(12)),self.outputs[0])
        code="from sampler_layer3_support import *; from threadpoolctl import threadpool_limits;\nwith threadpool_limits(limits=1): print(json.dumps(evaluate(*system(12)),sort_keys=True))"
        env=dict(os.environ,PYTHONPATH=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')]),JAX_PLATFORMS='cpu',JAX_ENABLE_X64='true',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        result=json.loads(subprocess.check_output([sys.executable,'-B','-c',code],env=env,text=True))
        self.assertEqual(result,self.outputs[0])


class RejectionTests(unittest.TestCase):
    def setUp(self):self.t,self.s,self.p=system()

    def test_rule_permutation_corruption_and_schema(self):
        r=self.t.rule;expected=json.loads(r.identity_json)
        for change in ('permutation','weight','nan','missing'):
            d={k:v.copy() for k,v in r.arrays.items()}
            if change=='permutation':d={k:v[::-1].copy() for k,v in d.items()}
            if change=='weight':d['weights'][0]*=2
            if change=='nan':d['omega'][0,0]=np.nan
            if change=='missing':del d['sqrt_weights']
            with self.assertRaises((ValueError,AssertionError)):FrozenRule.authenticate(d,expected)
        for key,value in [('ell_eta',.18),('feature_order','sine_then_cosine'),('artifact_sha256','a'*64),('x64_required',False),('schema','bad')]:
            e=copy.deepcopy(expected);e[key]=value
            with self.assertRaises(ValueError):FrozenRule.authenticate(dict(r.arrays),e)
            with self.assertRaises(ValueError):replace(r,identity_json=json.dumps(e)).validate()

    def test_x64_and_registry_mutation_rejection(self):
        with jax.experimental.enable_x64(False):
            with self.assertRaises(ValueError):self.t.rule.validate()
        with patch('bsfm.sampler.rule.REGISTRY_SHA256','0'*64):
            with self.assertRaises(ValueError):load_rule()

    def test_cell_coordinate_and_source_row_join_rejection(self):
        for key in ('cell_names','slocs','source_row_indices','gene_names'):
            data={k:v.copy() for k,v in self.t.inputs.arrays.items()}
            if key=='source_row_indices':data[key]+=10
            elif key=='slocs':data[key]+=.01
            else:data[key]=data[key][::-1].copy()
            identity=contracts.input_identity(data,section='synthetic',response_sha256='a'*64,coordinate_system='october26_glial_min_max_span')
            inputs=contracts.ModelInput.authenticate(data,identity)
            if key=='gene_names':
                other=DirectWTarget(inputs,self.t.geometry,self.t.rule,factor_ids=self.t.factor_ids)
                with self.assertRaises(ValueError):other.value_grad(self.p,self.s,state_factor_ids=self.t.factor_ids)
            else:
                with self.assertRaises(ValueError):DirectWTarget(inputs,self.t.geometry,self.t.rule,factor_ids=self.t.factor_ids)

    def test_factor_state_and_position_identity(self):
        for ids in (('factor-b','factor-a'),('a',),['factor-a','factor-b']):
            with self.assertRaises(ValueError):self.t.value_grad(self.p,self.s,state_factor_ids=ids)
        for p in (replace(self.p,target_identity='{}'),replace(self.p,factor_id='unknown'),replace(self.p,values=np.zeros(7))):
            with self.assertRaises(ValueError):self.t.value_grad(p,self.s,state_factor_ids=self.t.factor_ids)
        other=copy.deepcopy(self.s);other.input_identity_json='{}'
        with self.assertRaises(ValueError):self.t.value_grad(self.p,other,state_factor_ids=self.t.factor_ids)

    def test_malformed_parameters_and_rng_preservation(self):
        rng=np.random.default_rng(22);before=copy.deepcopy(rng.bit_generator.state)
        for index,value in [(0,np.inf),(0,1000.),(0,-1000.),(1,1000.),(1,-1000.),(2,np.nan),(4,np.inf)]:
            values=self.p.values.copy();values[index]=value;p=replace(self.p,values=values)
            with self.assertRaises(ValueError):self.t.draw_eta(p,self.s,rng,state_factor_ids=self.t.factor_ids)
            self.assertEqual(rng.bit_generator.state,before)
        for z in (np.zeros((3,1)),np.zeros((3,3)),np.full((3,2),np.nan)):
            with self.assertRaises(ValueError):self.t.position('factor-b',log_alpha=0.,logit_zeta=0.,log_ell=0.,log_r=0.,zW=z)
        bad=copy.deepcopy(self.s);bad.sigma2[0]=0.
        with self.assertRaises(ValueError):self.t.draw_eta(self.p,bad,rng,state_factor_ids=self.t.factor_ids)
        self.assertEqual(rng.bit_generator.state,before)

    def test_replaced_static_binding_rejected(self):
        self.t.factor_ids=('factor-b','factor-a')
        with self.assertRaises(ValueError):self.t.features(self.p)


if __name__=='__main__':unittest.main()
