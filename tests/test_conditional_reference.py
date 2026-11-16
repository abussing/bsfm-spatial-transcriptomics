"""Numerical-reference checks against known normalized Gaussian distributions."""
import unittest
import numpy as np
from bsfm.sampler.conditional_reference import conditional_reference

class ConditionalReferenceTests(unittest.TestCase):
    def test_correlated_gaussian_normalizer_and_moments(self):
        mean=np.array([.4,-2.,.8])
        cov=np.array([[.03,.014,0.],[.014,.6,.08],[0.,.08,.2]])
        H=np.linalg.inv(cov)
        normalizer=.5*(3*np.log(2*np.pi)+np.linalg.slogdet(cov)[1])
        def vg(q):
            delta=q-mean
            return -.5*delta@H@delta-normalizer,-H@delta
        summary,points,w=conditional_reference(vg,[mean+1,mean-1],seed=25,power=12)
        for row in summary["replicates"]:
            self.assertLess(abs(row["log_normalizer"]),.035)
            self.assertGreater(row["weight_ess"],800)
        got=w@points;delta=points-got
        np.testing.assert_allclose(got,mean,atol=.025)
        np.testing.assert_allclose(delta.T@(w[:,None]*delta),cov,atol=.035)
        self.assertAlmostEqual(w.sum(),1.,places=12)

    def test_reference_is_bounded(self):
        with self.assertRaises(ValueError):
            conditional_reference(lambda x:(0.,x),[np.zeros(3)],seed=1,power=20)

