"""Coordinate identity, full target derivative, and density measure checks."""
import unittest
import jax
jax.config.update('jax_enable_x64',True)
import jax.numpy as jnp
import numpy as np
from bsfm.sampler.variance_coordinates import to_variances,to_original,wrap_value_grad
from test_flat_range import setup
from bsfm.sampler.run_initialization import initialize
from pathlib import Path
import tempfile


class VarianceCoordinatesTests(unittest.TestCase):
    def test_covariance_and_measure(self):
        phi=np.random.default_rng(3).normal(size=(7,4))
        for a in [-4.,0.,3.]:
            for b in [-15.,-2.,0.,2.,15.]:
                q=jnp.array([a,b,-1.7,2.])
                x=to_variances(q)
                np.testing.assert_allclose(to_original(x),q,atol=4e-15,rtol=1e-14)
                z=float(jax.nn.sigmoid(b))
                original=np.exp(2*a)*(z*phi@phi.T+(1-z)*np.eye(7))
                changed=np.exp(float(x[0]))*phi@phi.T+np.exp(float(x[1]))*np.eye(7)
                np.testing.assert_allclose(changed,original,atol=1e-10,rtol=1e-12)
                self.assertAlmostEqual(float(jnp.linalg.det(jax.jacfwd(to_original)(x))),-.5,places=13)

    def test_general_density_gradient(self):
        # Nonseparable density: tests cross terms and unchanged tail coordinates.
        A=jnp.array([[2.,.4,.2],[.4,3.,-.3],[.2,-.3,1.]])
        density=lambda q: -.5*q@A@q+jnp.sin(q[0]*q[2])
        target=wrap_value_grad(jax.value_and_grad(density))
        for x in [jnp.array([2.,-3.,.2]),jnp.array([-4.,3.,-2.])]:
            v,g=target(x)
            ev,eg=jax.value_and_grad(lambda t:density(to_original(t))-jnp.log(2.))(x)
            np.testing.assert_allclose(v,ev,atol=1e-13)
            np.testing.assert_allclose(g,eg,atol=1e-13)

    def test_canonical_flat_full_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            c=setup(Path(tmp)/'unused');t=c.target
            e,_=initialize(t,c.loading,c.eta,seed=491)
            u,ct,penalty,_=t.context(e.state,factor_id=t.factor_ids[0],state_factor_ids=t.factor_ids)
            original=jax.jit(t._kernels['value_grad'])
            changed=jax.jit(wrap_value_grad(original))
            for b in [-8.,0.,8.]:
                q=jnp.array([.3,b,np.log(.18)]);x=to_variances(q)
                ov,_=original(q,u,ct,penalty);v,g=changed(x,u,ct,penalty)
                np.testing.assert_allclose(v+jnp.log(2.),ov,atol=1e-9,rtol=1e-10)
                for direction in np.eye(3):
                    h=1e-5
                    fd=(changed(x+h*direction,u,ct,penalty)[0]-changed(x-h*direction,u,ct,penalty)[0])/(2*h)
                    np.testing.assert_allclose(fd,g@direction,atol=2e-5,rtol=2e-5)

if __name__=='__main__':unittest.main()
