"""Exact active marginal via historical QR/JVP; no precision sub-block inverse."""
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
import numpy as np
from .spectral import spectral_modal_geometry

WHITENING_METHOD = "unguarded_positive_diagonal_qr_v1"


def _positive_qr_root(B):
    """Compress the full spectral factor without forming its Gram matrix.

    For full-row-rank B, positive-diagonal QR(B.T) gives the unique
    lower-triangular root of B @ B.T. No jitter or modes are added/dropped.
    """
    R = jnp.linalg.qr(B.T, mode="reduced")[1]
    signs = jnp.where(jnp.diag(R) < 0.0, -1.0, 1.0)
    return (signs[:, None] * R).T


def active_geometry(log_ell, U_active, spectral):
    """Return L and dL/dlog(ell) for Sigma_A = (U_A D)(U_A D)^T.

    Inactive full-mesh vertices are integrated out exactly.  This is not a
    conditional fill-in. QR preserves the intended raw-Q covariance without
    the former roundoff guard. Its directional derivative is evaluated
    through QR itself, never through a rounded covariance Cholesky.
    """
    geo = spectral_modal_geometry(
        log_ell,
        spectral["log_modal_diagonals"], spectral["log_coefficients"],
        spectral["powers"], spectral["log_kappa_constant"],
        spectral["log_trace_mass"], spectral["log_reference_variance"],
    )
    UA = jnp.asarray(U_active, jnp.float64)
    B = UA * geo["modal_sd"][None, :]
    Br = UA * geo["modal_sd_r"][None, :]
    L, L_r = jax.jvp(_positive_qr_root, (B,), (Br,))
    # Retain the diagnostic return contract. Neither Gram matrix is used
    # to compute the whitening root or its derivative.
    Sigma = B @ B.T
    Sigma_r = Br @ B.T + B @ Br.T
    return L, L_r, Sigma, Sigma_r, geo


def physical_active(log_ell, z, warp_sd, A_active, U_active, spectral):
    L, L_r, Sigma, Sigma_r, geo = active_geometry(
        log_ell, U_active, spectral)
    z = jnp.asarray(z, jnp.float64)
    A = jnp.asarray(A_active, jnp.float64)
    WA = float(warp_sd) * (L @ z)
    WA_r = float(warp_sd) * (L_r @ z)
    Wcell = A @ WA
    Wcell_r = A @ WA_r
    return Wcell, Wcell_r, WA, L, L_r, Sigma, Sigma_r, geo


def dense_active_covariance(U_active, modal_sd):
    B = np.asarray(U_active) * np.asarray(modal_sd)[None, :]
    return B @ B.T
