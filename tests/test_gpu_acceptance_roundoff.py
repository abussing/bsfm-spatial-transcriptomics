"""Only the documented probability-roundoff interval may be repaired."""
import unittest
import jax
import jax.numpy as jnp
import numpy as np
from bsfm.sampler.split_kernels import gpu_acceptance_roundoff

class GPUAcceptanceRoundoff(unittest.TestCase):
    def test_exact_bound_and_invalid_values(self):
        eps=np.finfo(np.float64).eps
        raw=np.array([0.,.9,1.,1+eps,1+8*eps,1+9*eps,-eps,np.inf,np.nan])
        actual=np.asarray(jax.jit(gpu_acceptance_roundoff)(jnp.asarray(raw)))
        expected=raw.copy();expected[3:5]=1.
        np.testing.assert_array_equal(actual,expected)

if __name__=='__main__':unittest.main()
