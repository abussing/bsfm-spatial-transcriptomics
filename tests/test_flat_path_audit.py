"""Independent quadratic-oracle checks for diagnostic integration and metric units."""
import unittest
import numpy as np
from bsfm.sampler.flat_path_audit import curvature,probe,swapped

class FlatPathAuditTests(unittest.TestCase):
    def setUp(self):
        self.h=np.array([[3.,.7,0.],[.7,2.,.2],[0.,.2,1.]])
        self.vg=lambda q:(-.5*q@self.h@q,-self.h@q)
        self.q=np.array([.3,-.7,.2]);self.p=np.array([.5,.4,-.1]);self.d=np.array([.2,3.,1.5])

    def test_hessian_uses_inverse_mass_convention(self):
        got=curvature(self.vg,self.q,self.d,.12)
        root=np.sqrt(self.d);expected=root[:,None]*self.h*root[None,:]
        np.testing.assert_allclose(got['hessian'],self.h,atol=1e-10)
        np.testing.assert_allclose(got['mass_scaled_eigenvalues'],np.linalg.eigvalsh(expected),atol=1e-10)
        self.assertAlmostEqual(got['local_step_number'],.12*np.sqrt(np.linalg.eigvalsh(expected)[-1]))

    def test_leapfrog_matches_independent_matrix_and_is_reversible(self):
        h=.1;n=8;D=np.diag(self.d);I=np.eye(3)
        kick=np.block([[I,np.zeros((3,3))],[-h*self.h/2,I]])
        drift=np.block([[I,h*D],[np.zeros((3,3)),I]])
        end=np.linalg.matrix_power(kick@drift@kick,n)@np.r_[self.q,self.p]
        got=probe(self.vg,self.q,self.p,self.d,h,n)
        np.testing.assert_allclose(got['rows'][-1]['q'],end[:3],atol=1e-13)
        rev=probe(self.vg,end[:3],end[3:],self.d,-h,n)
        np.testing.assert_allclose(rev['rows'][-1]['q'],self.q,atol=1e-13)
        H=lambda q,p:.5*q@self.h@q+.5*p@D@p
        self.assertAlmostEqual(got['rows'][-1]['energy_error'],H(end[:3],end[3:])-H(self.q,self.p))

    def test_resolution_comparison_keeps_duration(self):
        a=probe(self.vg,self.q,self.p,self.d,.12,8)
        b=probe(self.vg,self.q,self.p,self.d,.03,32)
        self.assertEqual(a['integration_duration'],b['integration_duration'])
        self.assertLess(b['max_abs_energy_error'],a['max_abs_energy_error']/8)

    def test_negative_curvature_not_given_positive_condition_number(self):
        h=np.diag([-2.,1.,3.]);vg=lambda q:(-.5*q@h@q,-h@q)
        r=curvature(vg,self.q,self.d,.1)
        self.assertTrue(r['negative_curvature']);self.assertIsNone(r['condition_number'])

    def test_swaps_leave_sources_and_unselected_inputs_unchanged(self):
        a=dict(position=np.array([1.,2.,3.]),u=np.array([4.]),ct=np.array([5.]),penalty=np.array(6.))
        b={k:v+10 for k,v in a.items()}
        result=swapped(a,b,['ct','alpha_only'])
        np.testing.assert_array_equal(result['position'],[11.,2.,3.])
        np.testing.assert_array_equal(result['ct'],b['ct'])
        np.testing.assert_array_equal(result['u'],a['u'])
        result['u'][0]=99;self.assertEqual(a['u'][0],4.)

    def test_nonfinite_path_is_flagged(self):
        def vg(q):
            if np.linalg.norm(q)>2:return -np.inf,np.zeros(3)
            return self.vg(q)
        r=probe(vg,self.q,self.p*10,self.d,1.,8)
        self.assertIsNotNone(r['failure'])
