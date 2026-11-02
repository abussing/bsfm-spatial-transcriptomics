"""Full-mode raw-Q FEM law; selected F source, not a geometry builder.

See docs/sampler/LAYER2_SOURCE_MAP.csv. Diagnostic variance never rescales Q.
Low-level modal functions are differentiable kernels; use WarpGeometry for
validated identities and finite-domain checks at the public boundary.
"""
import hashlib
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
import jax.scipy as jsp
import numpy as np
import scipy.linalg as sla
from scipy.special import logsumexp as scipy_logsumexp


def _relative_frobenius(a, b):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    return float(np.linalg.norm(a - b, "fro") /
                 max(np.finfo(np.float64).tiny, np.linalg.norm(b, "fro")))


def _sha(array):
    x = np.ascontiguousarray(np.asarray(array))
    return hashlib.sha256(x.view(np.uint8)).hexdigest()


def build_spectral_fem_artifact(
    mass, stiff_list, binomcoeffs, normconst, nu_fem, d_fem, A_proj,
    *, orthogonality_tolerance=2e-10,
    simultaneous_diagonal_tolerance=2e-10,
    eigen_residual_tolerance=2e-10,
):
    """Build and authenticate the fixed full-rank generalized eigenbasis.

    ``scipy.linalg.eigh(G1, M)`` returns columns ``U`` satisfying
    ``U.T @ M @ U = I``.  Every R-produced FEM polynomial term is then
    required to be diagonal in that same basis.  Failure is fatal: the code
    never silently drops off-diagonal terms or turns this into an
    approximation.
    """
    mass = np.asarray(mass, np.float64)
    stiff = tuple(np.asarray(x, np.float64) for x in stiff_list)
    binom = np.asarray(binomcoeffs, np.float64)
    A = np.asarray(A_proj, np.float64)
    if mass.ndim != 2 or mass.shape[0] != mass.shape[1]:
        raise ValueError("mass must be square")
    n = mass.shape[0]
    if not stiff or any(x.shape != (n, n) for x in stiff):
        raise ValueError("invalid FEM stiffness family")
    if binom.shape != (len(stiff) + 1,):
        raise ValueError("binomial coefficient/FEM order mismatch")
    if A.shape[1] != n:
        raise ValueError("A_proj/FEM dimension mismatch")

    eigenvalues, U = sla.eigh(stiff[0], mass, check_finite=True)
    identity = np.eye(n, dtype=np.float64)
    mass_gram = U.T @ mass @ U
    mass_orthogonality = _relative_frobenius(mass_gram, identity)
    eig_residual = float(
        np.linalg.norm(stiff[0] @ U - mass @ (U * eigenvalues[None, :]), "fro")
        / max(np.finfo(np.float64).tiny,
              np.linalg.norm(stiff[0] @ U, "fro")))

    transformed = [mass_gram]
    offdiag_relative = []
    diagonals = []
    for matrix in (mass,) + stiff:
        transformed_matrix = U.T @ matrix @ U
        diagonal = np.diag(transformed_matrix).copy()
        offdiag = transformed_matrix - np.diag(diagonal)
        relative = float(
            np.linalg.norm(offdiag, "fro") /
            max(np.finfo(np.float64).tiny,
                np.linalg.norm(transformed_matrix, "fro")))
        offdiag_relative.append(relative)
        # Roundoff-scale negative modal entries are clipped only after a
        # scale-aware authentication.  A material negative value is fatal.
        negative_tolerance = 2e-12 * max(1.0, float(np.max(np.abs(diagonal))))
        if float(np.min(diagonal)) < -negative_tolerance:
            raise RuntimeError(
                "FEM modal diagonal has a material negative entry: "
                f"{float(np.min(diagonal))}")
        diagonals.append(np.maximum(diagonal, 0.0))

    max_offdiag = max(offdiag_relative)
    if mass_orthogonality > orthogonality_tolerance:
        raise RuntimeError(
            f"generalized eigenbasis mass orthogonality failed: "
            f"{mass_orthogonality}")
    if eig_residual > eigen_residual_tolerance:
        raise RuntimeError(
            f"generalized eigenpair residual failed: {eig_residual}")
    if max_offdiag > simultaneous_diagonal_tolerance:
        raise RuntimeError(
            "FEM terms are not simultaneously diagonal in the generalized "
            f"basis: {max_offdiag}")

    modal_diagonals = np.stack(diagonals)
    positive = modal_diagonals > 0.0
    if np.any(np.sum(positive, axis=0) == 0):
        raise RuntimeError("at least one FEM mode has zero precision in all terms")
    log_modal_diagonals = np.full_like(modal_diagonals, -np.inf)
    log_modal_diagonals[positive] = np.log(modal_diagonals[positive])
    coefficients = float(normconst) * binom
    if np.any(coefficients <= 0.0):
        raise RuntimeError("spectral implementation requires positive SPDE coefficients")
    powers = float(d_fem) - 2.0 * np.arange(len(coefficients), dtype=np.float64)
    log_coefficients = np.log(coefficients)
    log_kappa_constant = 0.5 * np.log(8.0 * float(nu_fem))
    log_trace_mass = float(np.log(np.trace(mass)))
    projected_modes = A @ U

    # Reference variance uses the identical modal formula used in production.
    log_terms_ref = (
        log_coefficients[:, None]
        + powers[:, None] * log_kappa_constant
        + log_modal_diagonals
    )
    log_q_ref = np.asarray(scipy_logsumexp(log_terms_ref, axis=0), np.float64)
    log_reference_variance = float(
        scipy_logsumexp(-log_q_ref) - log_trace_mass)

    audit = {
        "status": "PASS",
        "n_v": int(n),
        "n_polynomial_terms": int(len(coefficients)),
        "full_rank_no_truncation": True,
        "mass_orthogonality_relative_frobenius": mass_orthogonality,
        "generalized_eigen_residual_relative_frobenius": eig_residual,
        "term_offdiagonal_relative_frobenius": offdiag_relative,
        "max_term_offdiagonal_relative_frobenius": max_offdiag,
        "generalized_eigenvalue_min": float(eigenvalues.min()),
        "generalized_eigenvalue_max": float(eigenvalues.max()),
        "log_reference_mass_variance": log_reference_variance,
        "basis_sha256": _sha(U),
        "modal_diagonals_sha256": _sha(modal_diagonals),
        "projected_modes_sha256": _sha(projected_modes),
    }
    return {
        "U": U,
        "projected_modes": projected_modes,
        "modal_diagonals": modal_diagonals,
        "log_modal_diagonals": log_modal_diagonals,
        "log_coefficients": log_coefficients,
        "powers": powers,
        "log_kappa_constant": log_kappa_constant,
        "log_trace_mass": log_trace_mass,
        "log_reference_variance": log_reference_variance,
        "audit": audit,
    }


def spectral_modal_geometry(
    log_ell, log_modal_diagonals, log_coefficients, powers,
    log_kappa_constant, log_trace_mass, log_reference_variance,
):
    """Return legacy raw-Q modal SDs and exact log-range derivatives.

    All polynomial evaluation is performed using log-sum-exp.  Derivatives of
    ``log q_i`` are weighted moments of the polynomial powers, avoiding large
    physical precision entries and cancellation.
    """
    r = jnp.asarray(log_ell, jnp.float64)
    log_diags = jnp.asarray(log_modal_diagonals, jnp.float64)
    log_coeff = jnp.asarray(log_coefficients, jnp.float64)
    powers = jnp.asarray(powers, jnp.float64)
    log_kappa = jnp.asarray(log_kappa_constant, jnp.float64) - r
    log_terms = (
        log_coeff[:, None]
        + powers[:, None] * log_kappa
        + log_diags
    )
    log_q = jsp.special.logsumexp(log_terms, axis=0)
    weights = jax.nn.softmax(log_terms, axis=0)
    minus_powers = -powers[:, None]
    log_q_r = jnp.sum(weights * minus_powers, axis=0)
    log_q_rr = (
        jnp.sum(weights * minus_powers * minus_powers, axis=0)
        - log_q_r * log_q_r
    )

    log_inverse_q = -log_q
    variance_weights = jax.nn.softmax(log_inverse_q)
    log_variance = (
        jsp.special.logsumexp(log_inverse_q)
        - jnp.asarray(log_trace_mass, jnp.float64)
    )
    minus_log_q_r = -log_q_r
    log_variance_r = jnp.sum(variance_weights * minus_log_q_r)
    log_variance_rr = (
        -jnp.sum(variance_weights * log_q_rr)
        + jnp.sum(variance_weights * minus_log_q_r * minus_log_q_r)
        - log_variance_r * log_variance_r
    )

    # Authoritative legacy direct-W FEM law: Q_used(ell) = Q_raw(ell).
    # The previous spectral implementation multiplied Q_raw by
    # V_raw(ell)/V_raw(1), which was a scientifically different
    # amplitude-normalized prior.  Retain the raw variance calculations above
    # only as diagnostics; they do not alter the coordinate map.
    log_amplitude_scale = jnp.asarray(0.0, jnp.float64)
    log_used_q = log_q
    log_used_q_r = log_q_r
    log_used_q_rr = log_q_rr
    modal_sd = jnp.exp(-0.5 * log_used_q)
    modal_sd_r = -0.5 * log_used_q_r * modal_sd
    modal_sd_rr = (
        0.25 * log_used_q_r * log_used_q_r
        - 0.5 * log_used_q_rr
    ) * modal_sd
    return {
        "modal_sd": modal_sd,
        "modal_sd_r": modal_sd_r,
        "modal_sd_rr": modal_sd_rr,
        "log_raw_q": log_q,
        "log_raw_q_r": log_q_r,
        "log_raw_q_rr": log_q_rr,
        "log_raw_mass_variance": log_variance,
        "log_raw_mass_variance_r": log_variance_r,
        "log_raw_mass_variance_rr": log_variance_rr,
        "log_amplitude_scale": log_amplitude_scale,
        "log_normalized_q": log_used_q,
        "legacy_raw_Q_prior": True,
    }
