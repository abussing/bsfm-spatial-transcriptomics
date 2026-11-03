"""Selected Layer-4 numerical kernels; see LAYER4_SOURCE_MAP.csv.

Trusted algebra only: public identity/domain validation is in layer4.py.
No driver, alternate branch, or runtime configuration side effects imported.
"""
from dataclasses import dataclass
from functools import partial
import jax
import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np


@dataclass(frozen=True)
class JointEtaDiagnostics:
    iterations: int
    relative_residual: float
    absolute_residual: float
    posterior_mahalanobis_RMS_error_upper_bound: float
    requested_posterior_mahalanobis_RMS_tolerance: float
    converged: bool
    minimum_h_eigenvalue: float
    maximum_h_asymmetry: float
    preconditioner_diagonal_minimum: float


def _joint_cell_statistics(y, loading, sigma2, cell_id, nugget_variance):
    """Return U_n, T_n^{-1}U_n, T_n^{-1}r_n for the C3 Gaussian model."""
    y = np.asarray(y, np.float64)
    loading = np.asarray(loading, np.float64)
    sigma2 = np.asarray(sigma2, np.float64)
    cell_id = np.asarray(cell_id, np.int64)
    if y.ndim != 2:
        raise ValueError("y must have shape (G,N)")
    cell_count, genes, factors = loading.shape
    if y.shape[0] != genes or sigma2.shape != (genes,):
        raise ValueError("loading/sigma2 dimensions do not match y")
    if cell_id.shape != (y.shape[1],) or np.any(cell_id < 0) or np.any(cell_id >= cell_count):
        raise ValueError("invalid cell_id")

    n = y.shape[1]
    u = np.empty((n, factors, factors), np.float64)
    r = np.empty((n, factors), np.float64)
    precision = 1.0 / sigma2
    for c in range(cell_count):
        rows = np.flatnonzero(cell_id == c)
        lam = loading[c]
        uc = lam.T @ (precision[:, None] * lam)
        u[rows] = uc
        r[rows] = (lam.T @ (precision[:, None] * y[:, rows])).T

    identity = np.eye(factors)[None, :, :]
    # T = I + U D^2.  Although T is not symmetric, T^{-1}U is symmetric PSD.
    t = identity + u * nugget_variance[None, None, :]
    h = np.linalg.solve(t, u)
    asymmetry = float(np.max(np.abs(h - np.swapaxes(h, 1, 2))))
    h = 0.5 * (h + np.swapaxes(h, 1, 2))
    s = np.linalg.solve(t, r[..., None]).squeeze(-1)
    return u, h, s, asymmetry


@jax.jit
def _block_preconditioner_cholesky(f, h):
    """Cholesky factors of Q_kk = I + F_k' diag(H_kk) F_k."""
    factors, _, columns = f.shape
    diagonal_h = jnp.diagonal(h, axis1=1, axis2=2).T
    blocks = jnp.eye(columns, dtype=jnp.float64)[None, :, :] + jnp.einsum(
        "knr,kn,kns->krs", f, diagonal_h, f, optimize=True
    )
    return jnp.linalg.cholesky(blocks)


@jax.jit
def _precision_matvec(f, h, x):
    projected = jnp.einsum("knr,kr->kn", f, x, optimize=True)
    coupled = jnp.einsum("nkl,ln->kn", h, projected, optimize=True)
    return x + jnp.einsum("knr,kn->kr", f, coupled, optimize=True)


@jax.jit
def _preconditioner_solve(cholesky, residual):
    return jax.vmap(lambda l, r: jsla.cho_solve((l, True), r))(
        cholesky, residual
    )


@partial(jax.jit, static_argnames=("maximum_iterations",))
def _pcg(f, h, cholesky, rhs, tolerance, maximum_iterations):
    x0 = jnp.zeros_like(rhs)
    residual0 = rhs
    z0 = _preconditioner_solve(cholesky, residual0)
    rz0 = jnp.vdot(residual0, z0).real
    rhs_norm = jnp.maximum(jnp.linalg.norm(rhs), jnp.asarray(1.0, jnp.float64))
    # Q = I + F' H F >= I.  If e is the beta solution error and r=Qe,
    # then e'Qe=r'Q^{-1}r <= ||r||^2.  Stopping at
    # ||r||/sqrt(dim(beta)) <= tolerance therefore gives a direct per-draw
    # upper bound on posterior-Mahalanobis RMS solve error.  A relative RHS
    # residual alone would not provide this guarantee.
    dimension_scale = jnp.sqrt(jnp.asarray(rhs.size, jnp.float64))
    absolute_target = tolerance * dimension_scale

    def condition(state):
        iteration, _, residual, _, _, _ = state
        return jnp.logical_and(
            iteration < maximum_iterations,
            jnp.linalg.norm(residual) > absolute_target,
        )

    def body(state):
        iteration, x, residual, direction, rz, _ = state
        q = _precision_matvec(f, h, direction)
        alpha = rz / jnp.vdot(direction, q).real
        x_new = x + alpha * direction
        residual_new = residual - alpha * q
        z_new = _preconditioner_solve(cholesky, residual_new)
        rz_new = jnp.vdot(residual_new, z_new).real
        beta = rz_new / rz
        direction_new = z_new + beta * direction
        return iteration + 1, x_new, residual_new, direction_new, rz_new, rhs_norm

    initial = (jnp.asarray(0, jnp.int32), x0, residual0, z0, rz0, rhs_norm)
    return jax.lax.while_loop(condition, body, initial)


def _precision_noise(rng, f, h):
    """Draw e with Cov(e)=I+F' H F without constructing that matrix."""
    factors, observations, columns = f.shape
    prior = rng.standard_normal((factors, columns))
    eigval, eigvec = np.linalg.eigh(h)
    minimum = float(np.min(eigval))
    if minimum < -2e-10:
        raise RuntimeError(f"cell coupling is not PSD: minimum eigenvalue {minimum}")
    eigval = np.maximum(eigval, 0.0)
    white = rng.standard_normal((observations, factors))
    cell_noise = np.einsum(
        "nij,nj->ni", eigvec, np.sqrt(eigval) * white, optimize=True
    )
    return prior + np.einsum("knr,nk->kr", f, cell_noise, optimize=True), minimum


def sample_joint_eta_pcg(
    rng,
    *,
    y,
    loading,
    alpha,
    sigma2,
    cell_id,
    zeta,
    features,
    tolerance=1e-10,
    maximum_iterations=80,
):
    """Draw all eta factors jointly to a certified numerical tolerance.

    ``features`` has shape (K,N,R) and represents the scientific TQFF paint
    before multiplication by sqrt(zeta).  ``loading`` is the model's actual
    Lambda and ``alpha`` is retained as the separate eta-prior scale.  The
    implementation temporarily solves in f=eta/alpha coordinates, using
    alpha*Lambda only as an internal algebraic contraction, and returns eta
    in the original model parameterization. ``tolerance`` is not an ordinary
    relative-residual threshold: it is the requested upper bound on the RMS
    beta-solve error in posterior-Mahalanobis units.  The bound follows from
    the certified structure Q = I + F' H F >= I.
    """
    rng = rng if isinstance(rng, np.random.Generator) else np.random.default_rng(rng)
    features = np.asarray(features, np.float64)
    zeta = np.asarray(zeta, np.float64)
    alpha = np.asarray(alpha, np.float64)
    factors, observations, columns = features.shape
    if zeta.shape != (factors,) or np.any(zeta <= 0.0) or np.any(zeta >= 1.0):
        raise ValueError("zeta must contain K values strictly between zero and one")
    if np.asarray(y).shape[1] != observations:
        raise ValueError("feature and observation counts differ")
    if alpha.shape != (factors,) or np.any(alpha <= 0.0):
        raise ValueError("alpha must contain K positive values")

    # Purely computational re-expression: Y = Lambda eta =
    # (Lambda alpha) f, where f has unit-scale TQFF prior.  Neither Lambda nor
    # alpha is overwritten or identified with this temporary matrix.
    scaled_loading = np.asarray(loading, np.float64) * alpha[None, None, :]

    smooth_sd = np.sqrt(zeta)
    nugget_sd = np.sqrt(1.0 - zeta)
    u, h, s, asymmetry = _joint_cell_statistics(
        y, scaled_loading, sigma2, cell_id, nugget_sd**2
    )
    f = smooth_sd[:, None, None] * features
    b = np.einsum("knr,nk->kr", f, s, optimize=True)
    noise, minimum_h = _precision_noise(rng, f, h)
    rhs = b + noise

    jf, jh, jrhs = map(jnp.asarray, (f, h, rhs))
    cholesky = _block_preconditioner_cholesky(jf, jh)
    iteration, beta, residual, _, _, rhs_norm = _pcg(
        jf,
        jh,
        cholesky,
        jrhs,
        jnp.asarray(float(tolerance), jnp.float64),
        maximum_iterations=int(maximum_iterations),
    )
    beta, residual = np.asarray(beta), np.asarray(residual)
    absolute_residual = float(np.linalg.norm(residual))
    relative_residual = float(absolute_residual / float(np.asarray(rhs_norm)))
    posterior_error_bound = float(absolute_residual / np.sqrt(rhs.size))
    converged = bool(posterior_error_bound <= tolerance)
    if not converged:
        raise RuntimeError(
            f"joint eta PCG failed: iterations={int(iteration)} "
            f"posterior_Mahalanobis_RMS_error_bound={posterior_error_bound:.3e} "
            f"tolerance={tolerance:.3e} relative_residual={relative_residual:.3e}"
        )

    eta_bar = np.einsum("knr,kr->kn", f, beta, optimize=True)
    scaled_loading = np.asarray(scaled_loading, np.float64)
    y = np.asarray(y, np.float64)
    sigma2 = np.asarray(sigma2, np.float64)
    cell_id = np.asarray(cell_id, np.int64)
    residual_y = y.copy()
    for c in range(scaled_loading.shape[0]):
        rows = np.flatnonzero(cell_id == c)
        residual_y[:, rows] -= scaled_loading[c] @ eta_bar[:, rows]

    eta = eta_bar.copy()
    identity = np.eye(factors)
    precision = 1.0 / sigma2
    for n in range(observations):
        lam = scaled_loading[cell_id[n]]
        un = u[n]
        p = identity + nugget_sd[:, None] * un * nugget_sd[None, :]
        lp = np.linalg.cholesky(p)
        weighted_residual = lam.T @ (precision * residual_y[:, n])
        rhs_xi = nugget_sd * weighted_residual
        mean_xi = np.linalg.solve(p, rhs_xi)
        xi = mean_xi + np.linalg.solve(lp.T, rng.standard_normal(factors))
        eta[:, n] += nugget_sd * xi

    preconditioner_diagonal = np.diagonal(np.asarray(cholesky), axis1=1, axis2=2)
    diagnostics = JointEtaDiagnostics(
        iterations=int(iteration),
        relative_residual=relative_residual,
        absolute_residual=absolute_residual,
        posterior_mahalanobis_RMS_error_upper_bound=posterior_error_bound,
        requested_posterior_mahalanobis_RMS_tolerance=float(tolerance),
        converged=converged,
        minimum_h_eigenvalue=minimum_h,
        maximum_h_asymmetry=asymmetry,
        preconditioner_diagonal_minimum=float(np.min(preconditioner_diagonal)),
    )
    return alpha[:, None] * eta, beta, diagnostics
