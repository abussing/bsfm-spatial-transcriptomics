"""Reusable numerical and resource tests; no study launcher or real section."""
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from numpy.testing import assert_allclose, assert_array_equal
from scipy.integrate import quad
from scipy.special import gamma
from bsfm.mesh import continuum, derivatives, fem, geometry, marginal
from bsfm.mesh import projectors, resources, spectral, support
from bsfm.mesh.identities import REPO, read_json


class NumericalTests(unittest.TestCase):
    def setUp(self):
        self.v=np.array([[0.,0.],[1.,0.],[0.,1.]])
        self.t=np.array([[0,1,2]],dtype='int64')

    def test_consistent_mass_and_stiffness_independent(self):
        m,g=fem.assemble(self.v,self.t)
        assert_allclose(m.toarray(),(np.ones((3,3))+np.eye(3))/24,atol=0,rtol=0)
        assert_allclose(g.toarray(),[[1,-.5,-.5],[-.5,.5,0],[-.5,0,.5]],atol=0,rtol=0)
        self.assertLess(max(fem.validate(self.v,self.t,m,g).values()),1e-15)

    def test_project_vertex_edge_interior_duplicate_nearby(self):
        xy=np.array([[0,0],[.5,0],[.2,.3],[.2,.3],[.2+1e-13,.3]])
        a=projectors.project(self.v,self.t,xy)
        assert_allclose(a.toarray(),np.c_[1-xy.sum(axis=1),xy],atol=1e-15)
        self.assertLessEqual(max(np.diff(a.indptr)),3)
        assert_allclose(a@self.v,xy,atol=1e-15)

    def test_outside_rejected(self):
        with self.assertRaises(ValueError):projectors.project(self.v,self.t,np.array([[1.,1.]]))

    def test_reversed_degenerate_and_one_based_rejected(self):
        for t in (self.t[:,[0,2,1]],np.array([[0,0,2]]),self.t+1,self.t.astype(float)):
            with self.subTest(t=t.tolist()),self.assertRaises(ValueError):geometry.triangles(self.v,t)

    def test_duplicate_triangles_rejected(self):
        with self.assertRaises(ValueError):geometry.triangles(self.v,np.vstack((self.t,self.t)))

    def test_canonical_vertex_triangle_order(self):
        v,t=geometry.canonicalize(self.v,self.t)
        order=np.array([2,0,1]);inv=np.argsort(order)
        v2,t2=geometry.canonicalize(self.v[order],inv[self.t][:,[0,2,1]])
        assert_array_equal(v,v2);assert_array_equal(t,t2)

    def test_full_spectrum_against_dense_precision_power(self):
        m,g=fem.assemble(self.v,self.t);md=m.toarray();gd=g.toarray()
        lam,u,report=spectral.spectrum(m,g)
        self.assertEqual(report['modes'],3);self.assertFalse(report['truncated'])
        for ell in [.15,.3,1.,3.,5.]:
            k2=40/ell**2;k=gd+k2*md;ki=np.linalg.inv(k)
            oracle=20*np.pi*k2**5*np.linalg.matrix_power(ki@md,5)@ki
            w,dw=spectral.modal(lam,ell);full=spectral.full_covariance(u,w)
            assert_allclose(full,oracle,rtol=2e-12,atol=2e-14)
            idx=np.array([0,2]);a=marginal.active_covariance(u,w,idx)
            assert_allclose(a,oracle[np.ix_(idx,idx)],rtol=2e-12,atol=2e-14)
            l,dl,ds=marginal.root_and_derivative(u,w,dw,idx)
            self.assertTrue(np.all(np.diag(l)>0));assert_array_equal(l,np.tril(l))
            assert_allclose(l@l.T,a,rtol=2e-14,atol=2e-14)
            assert_allclose(dl@l.T+l@dl.T,ds,rtol=2e-12,atol=2e-13)

    def test_derivatives_multiple_ranges_and_steps(self):
        m,g=fem.assemble(self.v,self.t);lam,u,_=spectral.spectrum(m,g)
        for ell in [.15,.3,1.,3.,5.]:
            result=derivatives.check(u,lam,np.array([0,2]),ell)
            self.assertLess(result['identity']['relative'],1e-12)
            self.assertEqual(len(result['finite_differences']),3)
            for row in result['finite_differences']:
                self.assertLess(row['covariance']['relative'],2e-5)
                self.assertLess(row['root']['relative'],2e-5)

    def test_matern_integral_oracle_and_limits(self):
        # Gamma mixture integral, independent of the implementation's Bessel call.
        for z in [0,1e-10,1e-4,.01,.5,1.,5.,15.]:
            oracle=quad(lambda t: t**4*np.exp(-t-z*z/(4*t))/gamma(5),0,np.inf,epsabs=2e-13,epsrel=2e-13)[0]
            actual=float(continuum.matern(z/np.sqrt(40),1))
            self.assertAlmostEqual(actual,oracle,places=12)
        self.assertEqual(float(continuum.matern(0,1)),1.)
        self.assertTrue(np.isfinite(continuum.matern([0,1e-300,1000],1)).all())
        with self.assertRaises(ValueError):continuum.matern([-1],1)

    def test_separated_clusters_connected_support_and_offsets(self):
        points=np.vstack((self.v,self.v+np.array([4.,0.])))
        h,c,o=support.enclosure(points,.2,.4,128)
        self.assertEqual(float(support.distance(np.array([[2.,.3]]),h)[0]),0.)
        self.assertLess(np.max(support.distance(points,c)),1e-12)
        self.assertGreater(o[:,0].max(),c[:,0].max())
        _,_,o2=support.enclosure(points,.2,.8,128)
        self.assertAlmostEqual(o2[:,0].max()-o[:,0].max(),.4,places=12)

    def test_edge_crossing_collar_min_distance(self):
        p=np.array([[0,0],[1,0],[1,1],[0,1]],float)
        assert_allclose(support.edge_distance(np.array([[-1,.5],[2,0]]),np.array([[2,.5],[2,1]]),p),[0,1],atol=1e-14)

    def test_headroom_rejection(self):
        with patch('bsfm.mesh.resources.psutil.virtual_memory') as vm:
            vm.return_value.available=7*resources.GiB
            with self.assertRaises(ValueError):resources.preflight()

    def test_memory_ceiling_terminates_worker_and_records_failure(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            with self.assertRaises(ValueError):resources.supervised([sys.executable,'-B','-c','import time; time.sleep(20)'],REPO,os.environ.copy(),d/'log',d/'record.json',ceiling_GiB=.001,minimum_GiB=0,poll_seconds=.01)
            rec=read_json(d/'record.json');self.assertEqual(rec['reason'],'process_tree_memory_ceiling')
            self.assertGreater(rec['peak_process_tree_bytes'],1024**2)

    def test_process_tree_child_detection(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d)
            command=[sys.executable,'-B','-c',"import subprocess,sys; subprocess.run([sys.executable,'-B','-c','import time; time.sleep(.4)'])"]
            rec=resources.supervised(command,REPO,os.environ.copy(),d/'log',d/'record.json',minimum_GiB=0,poll_seconds=.01)
            self.assertEqual(rec['status'],'pass');self.assertGreaterEqual(rec['maximum_children'],2)
