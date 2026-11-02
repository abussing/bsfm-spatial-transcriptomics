"""Selected direct-W factor kernels; no stochastic transition or adaptation."""
import jax
jax.config.update("jax_enable_x64", True)
import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np
from .active import active_geometry
from .finite_features import make_feature_kernel

def build_base_target(*, slocs, cell_vertex_idx, cell_weights, u_active, spectral, omega, sqrt_weights, mu_log_alpha, variance_log_alpha, a_zeta, b_zeta, loading_dimension, ell_eta_reference, mu_log_ell_u, variance_log_ell_u, mu_log_sigma_u, variance_log_sigma_u):
    """Selected fixed-ell_eta/live-warp base, called only by direct-W adapter."""
    live_ell_eta = False
    live_warp_hypers = True
    fixed_chol = None
    features_at, likelihood_parts, collapsed_likelihood_value = make_feature_kernel(omega, sqrt_weights)
    slocs = jnp.asarray(slocs, jnp.float64)
    indices = jnp.asarray(cell_vertex_idx, jnp.int32)
    weights = jnp.asarray(cell_weights, jnp.float64)
    u_active = jnp.asarray(u_active, jnp.float64)
    omega = jnp.asarray(omega, jnp.float64)
    sqrt_weights = jnp.asarray(sqrt_weights, jnp.float64)
    n_active = int(u_active.shape[0])
    mu_log_alpha = jnp.asarray(float(mu_log_alpha), jnp.float64)
    variance_log_alpha = jnp.asarray(float(variance_log_alpha), jnp.float64)
    a_zeta = jnp.asarray(float(a_zeta), jnp.float64)
    b_zeta = jnp.asarray(float(b_zeta), jnp.float64)
    loading_dimension = jnp.asarray(float(loading_dimension), jnp.float64)
    log_ell_eta_reference = jnp.log(jnp.asarray(float(ell_eta_reference), jnp.float64))
    warp_prior_values = (mu_log_ell_u, variance_log_ell_u, mu_log_sigma_u, variance_log_sigma_u)
    if any((value is None for value in warp_prior_values)):
        raise ValueError('live warp hypers require log-ell_U and log-sigma_U priors')
    mu_log_ell_u = jnp.asarray(float(mu_log_ell_u), jnp.float64)
    variance_log_ell_u = jnp.asarray(float(variance_log_ell_u), jnp.float64)
    mu_log_sigma_u = jnp.asarray(float(mu_log_sigma_u), jnp.float64)
    variance_log_sigma_u = jnp.asarray(float(variance_log_sigma_u), jnp.float64)
    if float(variance_log_ell_u) <= 0.0:
        raise ValueError('variance_log_ell_u must be positive')
    if float(variance_log_sigma_u) <= 0.0:
        raise ValueError('variance_log_sigma_u must be positive')

    def gather(active_values):
        return jnp.sum(weights[:, :, None] * active_values[indices], axis=1)

    def scatter(cell_gradient):
        contributions = weights[:, :, None] * cell_gradient[:, None, :]
        return jnp.zeros((n_active, 2), jnp.float64).at[indices.reshape(-1)].add(contributions.reshape(-1, 2))

    def unpack(position):
        cursor = 2
        log_ell_eta = log_ell_eta_reference
        log_ell_u = position[cursor]
        log_sigma_u = position[cursor + 1]
        cursor += 2
        return (position[0], position[1], log_ell_eta, log_ell_u, log_sigma_u, position[cursor:].reshape(n_active, 2))

    def warp_geometry(log_ell_u):
        return active_geometry(log_ell_u, u_active, spectral)[:2]

    def value_grad(position, u, ct, loading_penalty):
        log_alpha, logit_zeta, log_ell_eta, log_ell_u, log_sigma_u, z_u = unpack(position)
        chol_u, chol_u_r = warp_geometry(log_ell_u)
        sigma_u = jnp.exp(log_sigma_u)
        active_displacement = sigma_u * (chol_u @ z_u)
        wcell = slocs + gather(active_displacement)
        likelihood, w_gradient, _, alpha2, zeta, nugget_variance, smooth_variance, derivative_nugget, derivative_smooth, gradient_log_ell_eta = likelihood_parts(wcell, log_alpha, logit_zeta, log_ell_eta, u, ct)
        value = likelihood + loading_dimension * log_alpha - 0.5 * alpha2 * loading_penalty - 0.5 * (log_alpha - mu_log_alpha) ** 2 / variance_log_alpha + a_zeta * jnp.log(zeta) + b_zeta * jnp.log1p(-zeta) - 0.5 * jnp.sum(z_u * z_u)
        gradient_log_alpha = 2.0 * nugget_variance * derivative_nugget + 2.0 * smooth_variance * derivative_smooth + loading_dimension - alpha2 * loading_penalty - (log_alpha - mu_log_alpha) / variance_log_alpha
        gradient_logit_zeta = zeta * (1.0 - zeta) * alpha2 * (derivative_smooth - derivative_nugget) + a_zeta * (1.0 - zeta) - b_zeta * zeta
        active_gradient = scatter(w_gradient)
        gradient_z = sigma_u * (chol_u.T @ active_gradient) - z_u
        scalar_gradient = [gradient_log_alpha, gradient_logit_zeta]
        active_displacement_log_ell = sigma_u * (chol_u_r @ z_u)
        gradient_log_ell_u = jnp.sum(active_gradient * active_displacement_log_ell) - (log_ell_u - mu_log_ell_u) / variance_log_ell_u
        gradient_log_sigma_u = jnp.sum(active_gradient * active_displacement) - (log_sigma_u - mu_log_sigma_u) / variance_log_sigma_u
        value = value - 0.5 * (log_ell_u - mu_log_ell_u) ** 2 / variance_log_ell_u
        value = value - 0.5 * (log_sigma_u - mu_log_sigma_u) ** 2 / variance_log_sigma_u
        scalar_gradient.extend((gradient_log_ell_u, gradient_log_sigma_u))
        gradient = jnp.concatenate((jnp.asarray(scalar_gradient), gradient_z.reshape(-1)))
        return (value, gradient)

    def reference_value(position, u, ct, loading_penalty):
        log_alpha, logit_zeta, log_ell_eta, log_ell_u, log_sigma_u, z_u = unpack(position)
        chol_u = warp_geometry(log_ell_u)[0]
        sigma_u = jnp.exp(log_sigma_u)
        active_displacement = sigma_u * (chol_u @ z_u)
        wcell = slocs + gather(active_displacement)
        alpha2 = jnp.exp(2.0 * log_alpha)
        zeta = jax.nn.sigmoid(logit_zeta)
        likelihood = collapsed_likelihood_value(wcell, log_alpha, logit_zeta, log_ell_eta, u, ct)
        value = likelihood + loading_dimension * log_alpha - 0.5 * alpha2 * loading_penalty - 0.5 * (log_alpha - mu_log_alpha) ** 2 / variance_log_alpha + a_zeta * jnp.log(zeta) + b_zeta * jnp.log1p(-zeta) - 0.5 * jnp.sum(z_u * z_u)
        value = value - 0.5 * (log_ell_u - mu_log_ell_u) ** 2 / variance_log_ell_u
        value = value - 0.5 * (log_sigma_u - mu_log_sigma_u) ** 2 / variance_log_sigma_u
        return value

    def warp_features(position):
        _, _, log_ell_eta, log_ell_u, log_sigma_u, z_u = unpack(position)
        chol_u = warp_geometry(log_ell_u)[0]
        active_displacement = jnp.exp(log_sigma_u) * (chol_u @ z_u)
        wcell = slocs + gather(active_displacement)
        return (wcell, active_displacement, features_at(wcell, log_ell_eta)[4])

    def warp_state(position):
        _, _, log_ell_eta, log_ell_u, log_sigma_u, z_u = unpack(position)
        chol_u = warp_geometry(log_ell_u)[0]
        active_displacement = jnp.exp(log_sigma_u) * (chol_u @ z_u)
        wcell = slocs + gather(active_displacement)
        return (wcell, active_displacement, jnp.exp(log_ell_eta))

    def warp_hyper_state(position):
        _, _, log_ell_eta, log_ell_u, log_sigma_u, _ = unpack(position)
        return (jnp.exp(log_ell_eta), jnp.exp(log_ell_u), jnp.exp(log_sigma_u))
    return {'value_grad': value_grad, 'reference_value': reference_value, 'reference_value_grad': jax.value_and_grad(reference_value), 'warp_features': warp_features, 'warp_state': warp_state, 'warp_hyper_state': warp_hyper_state, 'fixed_chol': fixed_chol, 'n_active': n_active, 'live_ell_eta': live_ell_eta, 'live_warp_hypers': live_warp_hypers, 'warp_position_offset': 2 + int(live_ell_eta) + 2 * int(live_warp_hypers)}

def build_direct_target(**kwargs):
    kwargs = dict(kwargs)
    variance_log_r = float(kwargs.pop('variance_log_r_W', 0.09))
    if not np.isfinite(variance_log_r) or variance_log_r <= 0:
        raise ValueError('log-r variance must be finite and positive')
    offset = 0.5 * np.log(10.0)
    mu_ell = kwargs['mu_log_ell_u']
    if not np.allclose([kwargs['mu_log_sigma_u'], kwargs['variance_log_ell_u'], kwargs['variance_log_sigma_u']], [mu_ell - offset, 0.25, 0.25], rtol=0.0, atol=1e-12):
        raise ValueError('Direct-W test uses the declared common range/stretch prior')
    kwargs = dict(kwargs)
    kwargs['slocs'] = np.zeros_like(kwargs['slocs'])
    base = build_base_target(**kwargs)

    def translate(x):
        return x.at[3].set(x[2] + x[3] - offset)

    def correction(x):
        a, b = (x[2] - mu_ell, x[3])
        return (a + b) ** 2 / (2 * 0.25) - b * b / (2 * variance_log_r)

    def value_grad(x, u, ct, penalty):
        value, g = base['value_grad'](translate(x), u, ct, penalty)
        g = g.at[2].set(g[2] + g[3] + (x[2] - mu_ell + x[3]) / 0.25)
        g = g.at[3].add((x[2] - mu_ell + x[3]) / 0.25 - x[3] / variance_log_r)
        return (value + correction(x), g)

    def reference(x, u, ct, penalty):
        return base['reference_value'](translate(x), u, ct, penalty) + correction(x)
    result = dict(base)
    result.update(value_grad=value_grad, reference_value=reference, reference_value_grad=jax.value_and_grad(reference))
    for name in ('warp_features', 'warp_state', 'warp_hyper_state'):
        method = base[name]
        result[name] = lambda x, method=method: method(translate(x))
    return result
