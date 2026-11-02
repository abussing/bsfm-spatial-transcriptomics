"""Selected F/C functions only; see docs/sampler/LAYER1_SOURCE_MAP.csv.

Validation precedes RNG consumption. Mathematical bodies and random calls are preserved.
"""
import numpy as np
from . import contracts
from .shrinkage import compute_qgk
from .contracts import MU_LOG_ALPHA, VAR_LOG_ALPHA


def refresh_alpha_gauge(loading, eta, alpha, rng, s, label):
    """F/run_c3full_fixed_profile_nuts.py:182-230; source SHA-256 eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49."""
    contracts.px_inputs(loading, eta, alpha, rng, s, label)
    old_alpha = np.asarray(alpha, float).copy()
    new_alpha = np.exp(rng.normal(loc=MU_LOG_ALPHA, scale=np.sqrt(VAR_LOG_ALPHA), size=len(old_alpha)))
    loading0 = np.asarray(loading, float).copy()
    eta0 = np.asarray(eta, float).copy()
    q0 = compute_qgk(loading0, s, loading0.shape[0])
    identified_loading = loading0 * old_alpha[None, None, :]
    standardized_factor = eta0 / old_alpha[:, None]
    shrinkage_invariant = q0 * old_alpha[None, :] ** 2
    loading1 = loading0 * (old_alpha / new_alpha)[None, None, :]
    eta1 = eta0 * (new_alpha / old_alpha)[:, None]
    q1 = compute_qgk(loading1, s, loading1.shape[0])
    checks = {'identified_loading': float(np.max(np.abs(loading1 * new_alpha[None, None, :] - identified_loading))), 'standardized_factor': float(np.max(np.abs(eta1 / new_alpha[:, None] - standardized_factor))), 'signal': float(np.max(np.abs(np.einsum('cgk,kn->cgn', loading1, eta1) - np.einsum('cgk,kn->cgn', loading0, eta0)))), 'alpha2_q': float(np.max(np.abs(q1 * new_alpha[None, :] ** 2 - shrinkage_invariant)))}
    scales = {'identified_loading': max(1.0, float(np.max(np.abs(identified_loading)))), 'standardized_factor': max(1.0, float(np.max(np.abs(standardized_factor)))), 'signal': max(1.0, float(np.max(np.abs(np.einsum('cgk,kn->cgn', loading0, eta0))))), 'alpha2_q': max(1.0, float(np.max(np.abs(shrinkage_invariant))))}
    relative = {name: checks[name] / scales[name] for name in checks}
    if max(relative.values()) > 5e-13:
        raise RuntimeError(f'PX alpha refresh failed {label}: {relative}')
    contracts.array(loading1, 'PX Lambda', loading0.shape)
    contracts.array(eta1, 'PX eta', eta0.shape)
    contracts.array(new_alpha, 'PX alpha', old_alpha.shape, positive=True)
    return (loading1, eta1, new_alpha, {'label': label, 'old_alpha': old_alpha.tolist(), 'new_alpha': new_alpha.tolist(), 'checks_relative': relative, 'exact_prior_draw': True, 'identified_state_preserved': True})
