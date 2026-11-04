"""Mathematical tests for the GPU accumulation correction, executable on CPU."""
import unittest
from unittest.mock import patch
import jax
import jax.numpy as jnp
import numpy as np
from bsfm.sampler.gradient_accumulation import fixed_incidence_reducer
from sampler_layer3_support import system, dense_target


class AccumulationTests(unittest.TestCase):
    def test_repeated_indices_and_unused_vertex(self):
        idx = np.array([[2, 0, 2], [0, 2, 1], [2, 1, 2]])
        x = np.random.default_rng(41).normal(size=(idx.size, 2))
        expected = np.zeros((4, 2))
        np.add.at(expected, idx.reshape(-1), x)
        reduce = jax.jit(fixed_incidence_reducer(idx, 4))
        actual = np.asarray(reduce(x))
        np.testing.assert_allclose(actual, expected, rtol=2e-15, atol=2e-15)
        np.testing.assert_array_equal(actual[3], 0.)
        for _ in range(10):
            np.testing.assert_array_equal(actual, reduce(x))

    def test_full_target_with_fixed_reduction_against_dense_gaussian(self):
        # Exercise the GPU algebra on CPU without needing a CUDA installation.
        with patch('bsfm.sampler.field_kernels.jax.default_backend', return_value='gpu'):
            target, state, position = system()
        value, gradient, _ = target.value_grad(position, state, state_factor_ids=target.factor_ids)
        dense, dense_grad = jax.value_and_grad(
            lambda x: dense_target(target, state, position, x))(jnp.asarray(position.values))
        self.assertLessEqual(abs(value-float(dense))/max(1, abs(float(dense))), 2e-12)
        self.assertLessEqual(np.linalg.norm(gradient-np.asarray(dense_grad))/max(1, np.linalg.norm(dense_grad)), 2e-10)


if __name__ == '__main__':
    unittest.main()
