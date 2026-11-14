import unittest
import numpy as np
from bsfm.sampler.conditional_curvature_audit import lanczos_extremes,transport_field_inverse_mass

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

    def test_metric_preserves_physical_covariance_and_kinetic_energy(self):
        old=np.array([[1.2,0],[.4,.7]])
        new=np.array([[.8,0],[-.2,1.3]])
        mass=np.array([.4,.3,1.,2.,3.,4.])
        D=transport_field_inverse_mass(mass,old,new)
        B=np.kron(new,np.eye(2));R=np.kron(old,np.eye(2))
        np.testing.assert_allclose(B@D[2:,2:]@B.T,(R*mass[2:])@R.T,atol=1e-12)
        np.testing.assert_allclose(D[:2,:2],np.diag(mass[:2]))
        T=np.eye(6);T[2:,2:]=np.linalg.solve(B,R)
        p=np.arange(1.,7.);pn=np.linalg.solve(T.T,p)
        self.assertAlmostEqual(float(pn@D@pn),float(p@(mass*p)),places=11)
        np.linalg.cholesky(D)
