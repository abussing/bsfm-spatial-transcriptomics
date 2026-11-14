"""Exact host-level consistency of stored charts and physical state values."""
import jax
import jax.numpy as jnp
import numpy as np
from scipy.special import logit
from .migration_boundary import chart_migration_audit


def validate_chart_state(target, position, state, factor_index):
    """Accept exact inverse-recorded or historical forward values per coordinate.

    PX refreshes log-alpha independently of logit-zeta, so each coordinate may
    carry either convention. Ordinary checks are exact. Explicit runtime migration
    permits audited forward roundoff up to 16 eps; no values are rewritten.
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
    audit=chart_migration_audit.get()
    if (not alpha_ok or not zeta_ok) and audit is not None:
        # Imported values stay untouched. Only an explicitly scoped migration
        # may compare independent transcendental evaluations with roundoff.
        with np.errstate(over='ignore',invalid='ignore'):
            ae=0. if alpha_ok else float(abs(np.exp(p[0])-alpha)/alpha)
            ze=0. if zeta_ok else abs(float(jax.nn.sigmoid(jnp.asarray(p[1])))-zeta)/zeta
        tolerance=16*np.finfo(np.float64).eps
        if np.isfinite(ae+ze) and max(ae,ze)<=tolerance:
            audit.append(dict(factor_id=position.factor_id,alpha_relative_error=ae,
                              zeta_relative_error=ze,relative_tolerance=tolerance))
            return
    if not alpha_ok or not zeta_ok:
        raise ValueError('Position alpha/zeta mismatch with current state')
