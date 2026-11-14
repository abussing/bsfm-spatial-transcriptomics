"""Exact coordinates for the existing alpha/zeta target.

The opt-in flat_variances_v1 policy uses this chart. It changes coordinates, not
the priors, covariance, Gibbs chronology, or persisted position convention.
"""
import jax
import jax.numpy as jnp


def to_variances(position):
    """Replace log(alpha), logit(zeta) by log spatial/nugget VARIANCES."""
    a, b = position[:2]
    return position.at[0].set(2*a+jax.nn.log_sigmoid(b)).at[1].set(
        2*a+jax.nn.log_sigmoid(-b))


def to_original(position):
    s, n = position[:2]
    return position.at[0].set(.5*jnp.logaddexp(s,n)).at[1].set(s-n)


def wrap_value_grad(value_grad):
    """Pull back the FULL original density, including every existing prior.

    Absolute determinant d(log alpha,logit zeta)/d(s,n) is 1/2.
    This constant is retained in the value; it has zero gradient.
    """
    def transformed(position, *context):
        q=to_original(position)
        value, gradient=value_grad(q,*context)
        z=jax.nn.sigmoid(q[1])
        gs=.5*z*gradient[0]+gradient[1]
        gn=.5*(1-z)*gradient[0]-gradient[1]
        return value-jnp.log(2.),gradient.at[0].set(gs).at[1].set(gn)
    return transformed
