"""Exact host-level consistency of stored charts and physical state values."""
import jax
import jax.numpy as jnp
import numpy as np
from scipy.special import logit


def validate_chart_state(target, position, state, factor_index):
    """Accept exact inverse-recorded or historical forward values per coordinate.

    PX refreshes log-alpha independently of logit-zeta, so each coordinate may
    carry either convention. No tolerance, clipping or rewriting is performed.
    Full state/target identity validation remains the calling boundary's duty.
    """
    target._check_position(position)
    if (not isinstance(factor_index, (int, np.integer))
            or not 0 <= factor_index < len(target.factor_ids)
            or position.factor_id != target.factor_ids[factor_index]):
        raise ValueError('Ordered factor position mismatch')
    alpha, zeta = state.alpha[factor_index], state.zeta[factor_index]
    if (np.ndim(alpha) or np.ndim(zeta) or not np.isfinite(alpha)
            or alpha <= 0 or not np.isfinite(zeta) or not 0 < zeta < 1):
        raise ValueError('Invalid physical alpha/zeta domain')
    p = position.values
    alpha_ok = (p[0] == np.log(alpha)
                or alpha == float(np.exp(np.asarray(p[0]))))
    zeta_ok = (p[1] == logit(zeta)
               or zeta == float(jax.nn.sigmoid(jnp.asarray(p[1]))))
    if not alpha_ok or not zeta_ok:
        raise ValueError('Position alpha/zeta mismatch with current state')
