"""Deterministic full-spectrum foundation; no likelihood, MCMC or mesh construction."""
import ast
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import jax
import jax.numpy as jnp
import numpy as np
from scipy import sparse
from scipy.io import mmwrite
from threadpoolctl import threadpool_limits

from bsfm.mesh.october26 import marginal_root, spectral_artifact, warp_cells
from bsfm.sampler import warp, spectral, active
from bsfm.sampler.projector_encoding import barycentric_triplets
from sampler_layer2_support import ROOT, synthetic, authenticated, evaluate, port_functions, serial, relative

FIXTURE=json.loads((ROOT/'tests/fixtures/sampler_layer2.json').read_text(encoding='utf-8'))


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.limit=threadpool_limits(limits=1);cls.limit.__enter__()
        cls.data=synthetic();cls.g=authenticated(cls.data);cls.x=float(np.log(.3))
        cls.l,cls.lr,cls.cov,cls.covr,cls.geo=cls.g.geometry(cls.x)

    @classmethod
    def tearDownClass(cls):cls.limit.__exit__(None,None,None)

    def test_exact_historical_fixtures(self):
        for case in FIXTURE['cases']:
            actual=serial(evaluate(port_functions(),synthetic(case['scale']),float(np.log(case['ell']))))
            self.assertEqual(actual,case['expected'])

    def test_deterministic_repeat_and_fresh_process(self):
        a=serial(evaluate(port_functions(),self.data,self.x))
        self.assertEqual(a,serial(evaluate(port_functions(),self.data,self.x)))
        code="from sampler_layer2_support import *; print(json.dumps(serial(evaluate(port_functions(),synthetic(),float(np.log(.3)))),sort_keys=True))"
        env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')])
        env.update(JAX_PLATFORMS='cpu',JAX_ENABLE_X64='true',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
        child=json.loads(subprocess.check_output([sys.executable,'-B','-c',code],env=env,text=True))
        self.assertEqual(a,child)

    def test_generalized_eigen_and_all_modes(self):
        spec=self.g.spectral;u=spec['U'];m,g=self.data['terms'][:2]
        self.assertEqual(u.shape,(5,5));self.assertEqual(spec['modal_diagonals'].shape,(7,5))
        np.testing.assert_allclose(u.T@m@u,np.eye(5),atol=2e-10,rtol=0)
        ev=np.diag(u.T@g@u)
        self.assertLessEqual(relative(g@u,m@(u*ev)),2e-10)
        self.assertTrue(spec['audit']['full_rank_no_truncation'])

    def test_raw_modal_precision_formula_and_no_renormalization(self):
        for ell in [.3,1.]:
            geo=self.g.geometry(float(np.log(ell)))[4];spec=self.g.spectral
            q=np.sum((warp.NORMCONST*warp.BINOM)[:,None]*(np.sqrt(40)/ell)**(2-2*np.arange(7)[:,None])*spec['modal_diagonals'],axis=0)
            self.assertTrue(np.all(q>0))
            np.testing.assert_allclose(np.exp(geo['log_raw_q']),q,rtol=2e-10,atol=0)
            np.testing.assert_array_equal(geo['log_normalized_q'],geo['log_raw_q'])
            self.assertEqual(float(geo['log_amplitude_scale']),0.)
            # A diagnostic-only reference variance must have no effect on SDs.
            altered=dict(spec);altered['log_reference_variance']=1e6
            out=active.active_geometry(np.log(ell),spec['U'][self.data['active_indices']],altered)
            np.testing.assert_array_equal(out[4]['modal_sd'],geo['modal_sd'])

    def test_independent_dense_inverse_and_schur_marginal(self):
        t=self.data['terms'];kappa=np.sqrt(40)/np.exp(self.x)
        q=np.sum((warp.NORMCONST*warp.BINOM*kappa**(2-2*np.arange(7)))[:,None,None]*t,axis=0)
        full=np.linalg.inv(q);idx=self.data['active_indices'];out=np.setdiff1d(np.arange(5),idx)
        marginal=full[np.ix_(idx,idx)]
        schur=q[np.ix_(idx,idx)]-q[np.ix_(idx,out)]@np.linalg.solve(q[np.ix_(out,out)],q[np.ix_(out,idx)])
        self.assertLessEqual(relative(self.cov,marginal),2e-10)
        self.assertLessEqual(relative(self.cov,np.linalg.inv(schur)),2e-10)
        # This deliberately wrong conditional covariance must NOT match.
        self.assertGreater(relative(self.cov,np.linalg.inv(q[np.ix_(idx,idx)])),1e-3)

    def test_positive_qr_and_covariance_derivative(self):
        self.assertTrue(np.all(np.diag(self.l)>0))
        np.testing.assert_array_equal(np.triu(self.l,1),np.zeros_like(self.l))
        self.assertLessEqual(relative(self.l@self.l.T,self.cov),2e-10)
        self.assertLessEqual(relative(self.lr@self.l.T+self.l@self.lr.T,self.covr),2e-10)

    def test_first_and_second_modal_derivatives(self):
        s=self.g.spectral
        def fn(x):return spectral.spectral_modal_geometry(x,*[s[k] for k in ('log_modal_diagonals','log_coefficients','powers','log_kappa_constant','log_trace_mass','log_reference_variance')])
        for value,first,second in [('modal_sd','modal_sd_r','modal_sd_rr'),('log_raw_q','log_raw_q_r','log_raw_q_rr'),('log_raw_mass_variance','log_raw_mass_variance_r','log_raw_mass_variance_rr')]:
            d1=jax.jacfwd(lambda x:fn(x)[value])(self.x)
            d2=jax.jacfwd(jax.jacfwd(lambda x:fn(x)[value]))(self.x)
            np.testing.assert_allclose(d1,self.geo[first],rtol=2e-10,atol=2e-10)
            np.testing.assert_allclose(d2,self.geo[second],rtol=2e-10,atol=2e-10)

    def test_root_derivative_versus_covariance_identity(self):
        # Independent Cholesky differential identity, not differentiated QR.
        l=np.asarray(self.l);ds=np.asarray(self.covr)
        x=np.linalg.solve(l,np.linalg.solve(l,ds).T).T
        p=np.tril(x);p[np.diag_indices_from(p)]*=.5
        self.assertLessEqual(relative(l@p,self.lr),2e-10)

    def test_canonical_mesh_kernel_equivalence(self):
        u,d,audit=spectral_artifact(list(self.data['terms']))
        np.testing.assert_array_equal(u,self.g.spectral['U'])
        np.testing.assert_array_equal(d,self.g.spectral['modal_diagonals'])
        l,sd=marginal_root(u,d,self.data['active_indices'],np.exp(self.x))
        self.assertLessEqual(relative(l,self.l),2e-10)
        self.assertLessEqual(relative(sd,self.geo['modal_sd']),2e-10)

    def test_two_columns_physical_projection_and_coupled_amplitude(self):
        z=np.arange(len(self.l)*2,dtype=float).reshape(-1,2)/7
        r=.8;result=self.g.physical(self.x,np.log(r),z)
        sigma=np.exp(self.x)*r/np.sqrt(10)
        np.testing.assert_allclose(result['sigma_W'],sigma,rtol=2e-15,atol=0)
        np.testing.assert_allclose(result['W_active'],sigma*(self.l@z),rtol=2e-15,atol=0)
        aa=self.data['projector'][:,self.data['active_indices']]
        np.testing.assert_array_equal(result['W_cell'],np.asarray(aa)@np.asarray(result['W_active']))
        np.testing.assert_allclose(result['W_cell'],warp_cells(aa,np.asarray(result['W_active'])),rtol=2e-15,atol=0)
        ua=self.g.spectral['U'][self.data['active_indices']]
        f=lambda x: jnp.exp(x+np.log(r)-jnp.log(jnp.sqrt(10.)))*(active.active_geometry(x,ua,self.g.spectral)[0]@z)
        np.testing.assert_allclose(jax.jacfwd(f)(self.x),result['W_active_log_ell'],rtol=2e-10,atol=2e-10)
        np.testing.assert_array_equal(result['W_active_log_r'],result['W_active'])
        zero=self.g.physical(self.x,np.log(r),np.zeros_like(z))
        np.testing.assert_array_equal(zero['W_cell'],np.zeros((len(self.data['locations']),2)))
        same=self.g.physical(self.x,np.log(r),np.repeat(z[:,:1],2,axis=1))
        np.testing.assert_array_equal(same['W_cell'][:,0],same['W_cell'][:,1])

    def test_jit_and_directional_derivative_kernel(self):
        ua=self.g.spectral['U'][self.data['active_indices']]
        fn=lambda x:active.active_geometry(x,ua,self.g.spectral)
        compiled=jax.jit(fn)(self.x)
        for a,b in zip(compiled[:4],(self.l,self.lr,self.cov,self.covr)):
            np.testing.assert_allclose(a,b,rtol=2e-10,atol=2e-10)
        derivative=jax.jvp(lambda x:fn(x)[0],(jnp.asarray(self.x),),(jnp.asarray(1.),))[1]
        np.testing.assert_allclose(derivative,self.lr,rtol=2e-10,atol=2e-10)

    def test_rewhitening_preserves_physical_W(self):
        z=np.arange(len(self.l)*2,dtype=float).reshape(-1,2)/7
        wa=np.asarray(self.g.physical(self.x,np.log(.8),z)['W_active'])
        newz,check=self.g.rewhiten(wa,np.log(.7),np.log(.9))
        newwa=np.asarray(self.g.physical(np.log(.7),np.log(.9),newz)['W_active'])
        self.assertLessEqual(np.max(np.abs(newwa-wa)),2e-8)
        self.assertLessEqual(check['max_absolute_error'],2e-8)

    def test_projector_row_affine_and_triplets(self):
        a=self.data['projector'];idx=self.data['active_indices']
        np.testing.assert_allclose(a.sum(1),1,atol=5e-12,rtol=0)
        np.testing.assert_allclose(a@self.data['vertices'],self.data['locations'],atol=5e-12,rtol=0)
        i,w,_=barycentric_triplets(a[:,idx]);reconstructed=np.zeros_like(a[:,idx])
        for col in range(3):np.add.at(reconstructed,(np.arange(len(a)),i[:,col]),w[:,col])
        np.testing.assert_array_equal(reconstructed,a[:,idx])

    def test_dense_matrix_market_reuse(self):
        with tempfile.TemporaryDirectory() as tmp:
            for sparse_input in (False,True):
                x=self.data['terms'][0];path=Path(tmp)/'mass.mtx'
                mmwrite(path,sparse.csr_matrix(x) if sparse_input else x)
                np.testing.assert_array_equal(warp.dense_mm(path),x)

    def test_provenance_mathematical_bodies(self):
        with (ROOT/'docs/sampler/LAYER2_SOURCE_MAP.csv').open(encoding='utf-8') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),9)
        for row in rows:
            node=next(n for n in ast.parse((ROOT/row['port_path']).read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name==row['function'])
            self.assertEqual((node.lineno,node.end_lineno),(int(row['port_start']),int(row['port_end'])))
            body=node.body[1:] if ast.get_docstring(node) else node.body
            digest=hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False).encode()).hexdigest()
            self.assertEqual(digest,row['mathematical_body_ast_sha256'])


class RejectionTests(unittest.TestCase):
    def setUp(self):
        self.data=synthetic();self.identity=warp.mesh_identity(self.data,section='test',mesh_sha256='a'*64)

    def test_identity_order_and_value_rejection(self):
        for key in self.data:
            d=copy.deepcopy(self.data)
            if key in ('vertex_ids','cell_ids'):d[key]=d[key][::-1]
            else:d[key].flat[0]+=1
            with self.subTest(key=key),self.assertRaises((ValueError,RuntimeError)):
                warp.WarpGeometry.authenticate(d,self.identity)

    def test_malformed_identity(self):
        for key,value in [('schema','bad'),('axis_order',['center_x','center_y']),('units','microns'),('index_base',1),('law','normalized'),('mesh_sha256','invalid')]:
            expected=copy.deepcopy(self.identity);expected[key]=value
            with self.assertRaises(ValueError):warp.WarpGeometry.authenticate(self.data,expected)
        with self.assertRaises(ValueError):warp.WarpGeometry.authenticate(self.data,{})

    def test_shapes_finiteness_ids_and_partition(self):
        cases=[('terms',np.zeros((6,5,5))),('vertices',np.zeros((5,3))),
               ('active_indices',np.array([0,1,4,4])),('active_indices',np.array([1,0,4])),
               ('source_rows',np.zeros(3,dtype=int)),('cell_ids',np.array(['a','a','c'])),
               ('vertex_ids',np.arange(5)),('projector',np.ones((3,5))),
               ('locations',np.full((3,2),np.nan))]
        for key,value in cases:
            d=copy.deepcopy(self.data);d[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):warp.validate_mesh(d)
        for key in ('terms','vertices','projector','locations'):
            d=copy.deepcopy(self.data);d[key].flat[0]=np.inf
            with self.assertRaises(ValueError):warp.validate_mesh(d)

    def test_no_mutation_and_deliberate_mutation_detected(self):
        g=warp.WarpGeometry.authenticate(self.data,self.identity);self.data['terms'][0,0,0]+=1
        g.validate()
        with self.assertRaises(ValueError):g.arrays['terms'][0,0,0]=0
        g.spectral['U'].flags.writeable=True;g.spectral['U'][0,0]+=1
        with self.assertRaises(ValueError):g.validate()

    def test_nonpolynomial_asymmetric_or_negative_FEM_rejection(self):
        for mutate in ('asymmetric','nonpolynomial','negative','singular_mass'):
            d=copy.deepcopy(self.data)
            if mutate=='asymmetric':d['terms'][2,0,1]+=100
            if mutate=='nonpolynomial':d['terms'][2,0,0]+=1e6
            if mutate=='negative':d['terms'][2]*=-1
            if mutate=='singular_mass':d['terms'][0]*=0
            with self.subTest(mutate=mutate),self.assertRaises((ValueError,RuntimeError,np.linalg.LinAlgError)):
                expected=warp.mesh_identity(d,section='test',mesh_sha256='a'*64)
                warp.WarpGeometry.authenticate(d,expected)

    def test_field_shape_and_invalid_parameters(self):
        g=authenticated(self.data);n=len(g.arrays['active_indices'])
        for x in (np.nan,np.inf,-np.inf,1e4,-1e4,True,np.array([1.])):
            with self.assertRaises(ValueError):g.physical(x,0.,np.ones((n,2)))
        for z in (np.ones((n,1)),np.ones((n,3)),np.full((n,2),np.nan)):
            with self.assertRaises(ValueError):g.physical(0.,0.,z)
        with self.assertRaises(ValueError):g.rewhiten(np.ones((n,1)),0.,0.)

    def test_triplet_missing_row_extra_entries_and_small_value_rejection(self):
        for a in (np.zeros((1,3)),np.ones((1,4))*.25,np.array([[1-5e-14,5e-14,0.]])):
            with self.assertRaises(RuntimeError):barycentric_triplets(a)


if __name__=='__main__':unittest.main()
