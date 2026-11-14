"""Fixed reference whitening coordinates for the split field conditional.

W = B(x) z = B(ref) r. Sampling r with a fixed diagonal inverse mass is
equivalent to transporting that mass into z at each conditional. It does not
adapt from production history or introduce a position-dependent integrator.
"""
import jax.numpy as jnp
import jax.scipy.linalg as jla
import numpy as np


def build_reference_coordinates(kernels, maps, dimension, reference):
    n = (dimension - 4) // 2
    ref = jnp.asarray(reference, dtype=jnp.float64)
    B = maps['physical'](ref, jnp.eye(n))
    if not np.isfinite(B).all() or np.any(np.diag(B) <= 0):
        raise ValueError('Reference warp map must be finite and nonsingular')
    logdet_B = jnp.log(jnp.diag(B)).sum()

    def physical(xb, r):
        return B @ r

    def whiten(xb, W):
        return jla.solve_triangular(B, W, lower=True)

    def to_original(p):
        W = physical(p[2:4], p[4:].reshape(n, 2))
        return p.at[4:].set(maps['whiten'](p[2:4], W).ravel())

    def to_reference(p):
        W = maps['physical'](p[2:4], p[4:].reshape(n, 2))
        return p.at[4:].set(whiten(p[2:4], W).ravel())

    def log_jacobian(p):
        current_B = maps['physical'](p[2:4], jnp.eye(n))
        # Two independent physical warp columns, each with the same linear map.
        return 2 * (logdet_B - jnp.log(jnp.diag(current_B)).sum())

    def value_grad(p, *context):
        q = to_original(p)
        value, g = kernels['value_grad'](q, *context)
        T = maps['whiten'](p[2:4], B)
        gr = T.T @ g[4:].reshape(n, 2)
        W = physical(p[2:4], p[4:].reshape(n, 2))
        # In fixed physical coordinates the likelihood has no hyper derivative.
        gh = maps['value_grad'](p[2:4], W)[1]
        gradient = jnp.concatenate((g[:2], gh, gr.ravel()))
        return value + log_jacobian(p), gradient

    return dict(to_original=to_original, to_reference=to_reference,
                log_jacobian=log_jacobian, value_grad=value_grad,
                maps=dict(maps, physical=physical, whiten=whiten))
