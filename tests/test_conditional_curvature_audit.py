import unittest
import numpy as np
from bsfm.sampler.conditional_curvature_audit import lanczos_extremes

class CurvatureAuditTests(unittest.TestCase):
    def test_rotated_indefinite_matrix(self):
        rng=np.random.default_rng(921)
        q,_=np.linalg.qr(rng.normal(size=(12,12)))
        a=q@np.diag(np.linspace(-3,21,12))@q.T
        result,v=lanczos_extremes(lambda x:a@x,12,steps=12)
        self.assertAlmostEqual(result['minimum'],-3,places=9)
        self.assertAlmostEqual(result['maximum'],21,places=9)
        self.assertLess(result['residual'],1e-9)
        np.testing.assert_allclose(a@v,21*v,atol=1e-9)

    def test_repeated_eigenvalue(self):
        result,_=lanczos_extremes(lambda x:7*x,20)
        self.assertAlmostEqual(result['maximum'],7,places=10)
        self.assertEqual(result['iterations'],1)
