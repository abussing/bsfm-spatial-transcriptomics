"""Selected Layer-4 numerical kernels; see LAYER4_SOURCE_MAP.csv.

Trusted algebra only: public identity/domain validation is in layer4.py.
No driver, alternate branch, or runtime configuration side effects imported.
"""
import jax
import jax.numpy as jnp
import jax.scipy.linalg as jla
from .spectral import spectral_modal_geometry


def positive_qr_factor(B):
    Q, R = jnp.linalg.qr(B.T, mode='reduced')
    signs = jnp.where(jnp.diag(R) < 0., -1., 1.)
    return Q * signs[None, :], (signs[:, None] * R).T


def qr_contractions(Q, a, Z):
    """Return T=tr(L^-1 Lx), U=sum_c z_c.T L^-1 Lx z_c, not HZ."""
    leverage = jnp.sum(Q * Q, axis=1)
    QZ = Q @ Z
    return jnp.sum(a * leverage), jnp.sum(a[:, None] * QZ * QZ)


def spectral_qr_geometry(x, U_active, spectral):
    geo = spectral_modal_geometry(
        x, spectral['log_modal_diagonals'], spectral['log_coefficients'],
        spectral['powers'], spectral['log_kappa_constant'],
        spectral['log_trace_mass'], spectral['log_reference_variance'])
    B = U_active * geo['modal_sd'][None, :]
    Q, L = positive_qr_factor(B)
    # Direct log derivative, not modal_sd_r / modal_sd (avoid 0/0 underflow).
    a = -.5 * geo['log_raw_q_r']
    return Q, L, a


def build_centered_hyper_target(U_active, spectral):
    U_active = jnp.asarray(U_active, jnp.float64)
    n = U_active.shape[0]
    offset = .5 * jnp.log(10.)

    def geometry(x):
        return spectral_qr_geometry(x, U_active, spectral)

    def physical(xb, z):
        _, L, _ = geometry(xb[0])
        return jnp.exp(xb[0] + xb[1] - offset) * (L @ z)

    def whiten(xb, W):
        _, L, _ = geometry(xb[0])
        return jla.solve_triangular(L, W, lower=True) * jnp.exp(-xb.sum() + offset)

    def reference_value(xb, W):
        x, b = xb
        _, L, _ = geometry(x)
        Z = jla.solve_triangular(L, W, lower=True) * jnp.exp(-x-b+offset)
        return (-2*n*(x+b-offset) - 2*jnp.log(jnp.diag(L)).sum()
                - .5*jnp.sum(Z*Z) - .5*x*x/.25 - .5*b*b/.09)

    def evaluate(xb, W):
        x, b = xb
        Q, L, a = geometry(x)
        invscale = jnp.exp(-x-b+offset)
        Z = jla.solve_triangular(L, W, lower=True) * invscale
        S = jnp.sum(Z*Z)
        T, U = qr_contractions(Q, a, Z)
        value = (-2*n*(x+b-offset) - 2*jnp.log(jnp.diag(L)).sum()
                 - .5*S - .5*x*x/.25 - .5*b*b/.09)
        grad = jnp.array([-2*n-2*T+S+U-x/.25, -2*n+S-b/.09])
        return value, grad, L, Z, invscale

    def value_grad(xb, W):
        value, grad, _, _, _ = evaluate(xb, W)
        return value, grad

    @jax.custom_jvp
    def logdensity(xb, W):
        return reference_value(xb, W)

    @logdensity.defjvp
    def logdensity_jvp(primals, tangents):
        xb, W = primals
        dxb, dW = tangents
        value, grad, L, Z, invscale = evaluate(xb, W)
        # Reuse the SAME factorization if differentiation with respect to W
        # is requested. Fixed-W NUTS only requests xb derivatives.
        gradW = -jla.solve_triangular(L.T, Z, lower=False) * invscale
        return value, jnp.dot(grad, dxb) + jnp.sum(gradW*dW)

    return dict(logdensity=logdensity, reference_value=reference_value,
                value_grad=value_grad, physical=physical, whiten=whiten,
                geometry=geometry)
