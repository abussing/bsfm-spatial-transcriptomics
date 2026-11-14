import unittest
import jax
jax.config.update('jax_enable_x64',True)
import jax.numpy as jnp
import numpy as np
from bsfm.sampler.transition_replay_audit import energy_path


class EnergyDiagnosticTests(unittest.TestCase):
    def test_linear_hamiltonian_matrix_oracle(self):
        # Exact matrix representation of leapfrog for U=q^2/2 and unit mass.
        q=jnp.array([.7]);p=jnp.array([.2]);h=.1
        oracle=np.array([[1-h*h/2,h],[-h*(1-h*h/4),1-h*h/2]])
        initial=np.array([.7,.2]);state=initial.copy();expected=[]
        for _ in range(20):
            state=oracle@state;expected.append(.5*(state@state-initial@initial))
        got=energy_path(jax.value_and_grad(lambda x:-.5*jnp.sum(x*x)),q,p,jnp.ones(1),h,20)
        np.testing.assert_allclose(got,expected,atol=1e-15,rtol=1e-10)

    def test_fixed_duration_refinement(self):
        vg=jax.value_and_grad(lambda x:-.5*jnp.sum(x*x));errors=[]
        for n in [10,20,40]:
            errors.append(abs(float(energy_path(vg,jnp.array([1.]),jnp.array([.3]),jnp.ones(1),1/n,n)[-1])))
        self.assertTrue(3.8<errors[0]/errors[1]<4.2)
        self.assertTrue(3.8<errors[1]/errors[2]<4.2)

if __name__=='__main__':unittest.main()
