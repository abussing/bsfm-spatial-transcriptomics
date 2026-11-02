"""Frozen ordered L16 feature algebra. No exact-SE diagnostic enters this target."""
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np


def make_feature_kernel(omega, sqrt_weights):
    omega = jnp.asarray(omega, jnp.float64)
    sqrt_weights = jnp.asarray(sqrt_weights, jnp.float64)
    log_ell_eta_reference = jnp.log(jnp.asarray(.14, jnp.float64))
    identity = jnp.eye(2 * int(omega.shape[0]), dtype=jnp.float64)
    def features_at(wcell, log_ell_eta):
        frequency_scale = jnp.exp(log_ell_eta_reference - log_ell_eta)
        current_omega = frequency_scale * omega
        phase = wcell @ current_omega.T
        sin_phase, cos_phase = (jnp.sin(phase), jnp.cos(phase))
        scale = sqrt_weights[None, :]
        features = jnp.concatenate((cos_phase * scale, sin_phase * scale), axis=1)
        return (phase, sin_phase, cos_phase, scale, features, current_omega)

    def likelihood_parts(wcell, log_alpha, logit_zeta, log_ell_eta, u, ct):
        alpha2 = jnp.exp(2.0 * log_alpha)
        zeta = jax.nn.sigmoid(logit_zeta)
        nugget_variance = alpha2 * (1.0 - zeta)
        smooth_variance = alpha2 * zeta
        denominator = 1.0 + nugget_variance * u
        observation_weight = u / denominator
        sufficient = ct / denominator
        fixed_value = -0.5 * jnp.sum(jnp.log(denominator)) + 0.5 * jnp.sum(nugget_variance * ct * ct / denominator)
        phase, sin_phase, cos_phase, scale, features, current_omega = features_at(wcell, log_ell_eta)
        hessian = identity + smooth_variance * (features.T @ (observation_weight[:, None] * features))
        chol = jnp.linalg.cholesky(hessian)
        rhs = jnp.sqrt(smooth_variance) * (features.T @ sufficient)
        solved = jsla.cho_solve((chol, True), rhs)
        likelihood = fixed_value - jnp.sum(jnp.log(jnp.diag(chol))) + 0.5 * jnp.dot(rhs, solved)
        inverse_hessian = jsla.cho_solve((chol, True), identity)
        contraction = inverse_hessian + jnp.outer(solved, solved)
        phi_contraction = features @ contraction
        row_quadratic = jnp.sum(phi_contraction * features, axis=1)
        feature_gradient = -smooth_variance * (observation_weight[:, None] * phi_contraction) + jnp.sqrt(smooth_variance) * (sufficient[:, None] * solved[None, :])
        frequency_count = omega.shape[0]
        phase_gradient = scale * (-feature_gradient[:, :frequency_count] * sin_phase + feature_gradient[:, frequency_count:] * cos_phase)
        w_gradient = phase_gradient @ current_omega
        log_ell_eta_gradient = -jnp.sum(phase_gradient * phase)
        derivative_nugget = -0.5 * jnp.sum(observation_weight) + 0.5 * jnp.sum(ct * ct / (denominator * denominator)) + 0.5 * smooth_variance * jnp.sum(observation_weight * observation_weight * row_quadratic) - jnp.sqrt(smooth_variance) * jnp.sum(sufficient * observation_weight * (features @ solved))
        derivative_smooth = -0.5 * jnp.sum(observation_weight * row_quadratic) + 0.5 * jnp.dot(rhs, solved) / smooth_variance
        return (likelihood, w_gradient, features, alpha2, zeta, nugget_variance, smooth_variance, derivative_nugget, derivative_smooth, log_ell_eta_gradient)

    def collapsed_likelihood_value(wcell, log_alpha, logit_zeta, log_ell_eta, u, ct):
        """Independent value-only expression used to audit the hand gradient."""
        alpha2 = jnp.exp(2.0 * log_alpha)
        zeta = jax.nn.sigmoid(logit_zeta)
        nugget_variance = alpha2 * (1.0 - zeta)
        smooth_variance = alpha2 * zeta
        denominator = 1.0 + nugget_variance * u
        observation_weight = u / denominator
        sufficient = ct / denominator
        features = features_at(wcell, log_ell_eta)[4]
        hessian = identity + smooth_variance * (features.T @ (observation_weight[:, None] * features))
        chol = jnp.linalg.cholesky(hessian)
        rhs = jnp.sqrt(smooth_variance) * (features.T @ sufficient)
        solved = jsla.cho_solve((chol, True), rhs)
        return -0.5 * jnp.sum(jnp.log(denominator)) + 0.5 * jnp.sum(nugget_variance * ct * ct / denominator) - jnp.sum(jnp.log(jnp.diag(chol))) + 0.5 * jnp.dot(rhs, solved)
    return features_at, likelihood_parts, collapsed_likelihood_value
