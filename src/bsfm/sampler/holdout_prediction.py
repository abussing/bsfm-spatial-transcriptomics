"""Conditional omitted-cell prediction from retained training-only sampler states.

Prediction RNG is separate from chain RNG. Full-data SCT is a declared upstream
limitation, not an input to this conditional calculation. No query expression
is accepted by these functions.
"""
import numpy as np
from scipy.linalg import cho_factor, cho_solve, solve_triangular
from .spectral import spectral_modal_geometry


def features(w, rule):
    phase = np.asarray(w) @ rule.arrays['omega'].T
    scale = rule.arrays['sqrt_weights'][None, :]
    return np.concatenate((np.cos(phase)*scale, np.sin(phase)*scale), axis=1)


def conditional_warp(geometry, active_w, log_ell, sigma, query_projector, rng):
    """Draw full prior field conditional on retained active W via orthogonal factors."""
    s = geometry.spectral
    modal = spectral_modal_geometry(log_ell, s['log_modal_diagonals'], s['log_coefficients'],
        s['powers'], s['log_kappa_constant'], s['log_trace_mass'], s['log_reference_variance'])
    b = sigma*np.asarray(s['U'])*np.asarray(modal['modal_sd'])[None, :]
    indices = geometry.arrays['active_indices']
    q, r = np.linalg.qr(b[indices].T, mode='complete')
    n = len(indices)
    latent_mean = solve_triangular(r[:n, :].T, active_w, lower=True)
    latent = q[:, :n]@latent_mean + q[:, n:]@rng.standard_normal((b.shape[1]-n, 2))
    full = b@latent
    error = np.linalg.norm(full[indices]-active_w)/max(np.linalg.norm(active_w), 1e-100)
    if not np.isfinite(full).all() or error >= 2e-8:
        raise RuntimeError('Conditional warp failed retained-active reconstruction')
    return np.asarray(query_projector)@full


def conditional_factor(phi_train, eta_train, phi_query, alpha, zeta):
    """Return mean and marginal variance of eta_query conditional on eta_train."""
    smooth = alpha**2*zeta
    nugget = alpha**2*(1-zeta)
    if not np.isfinite([smooth,nugget]).all() or min(smooth,nugget)<=0:
        raise ValueError('Positive finite factor variances required')
    phi_train, phi_query = np.asarray(phi_train), np.asarray(phi_query)
    chol = cho_factor(np.eye(phi_train.shape[1])+(smooth/nugget)*(phi_train.T@phi_train), lower=True)
    beta = cho_solve(chol, (np.sqrt(smooth)/nugget)*(phi_train.T@eta_train))
    mean = np.sqrt(smooth)*(phi_query@beta)
    solved = cho_solve(chol, phi_query.T)
    variance = nugget+smooth*np.sum(phi_query*solved.T, axis=1)
    if not np.isfinite(mean).all() or not np.isfinite(variance).all() or np.any(variance<=0):
        raise RuntimeError('Invalid conditional prediction')
    return mean, variance


def predict_record(target, arrays, query_projector, query_locations, query_types, *, rng):
    """Conditional response means/variances for one committed posterior draw."""
    factors=len(target.factor_ids)
    if arrays['eta'].shape != (factors,len(target.inputs.arrays['slocs'])):
        raise ValueError('Training eta identity/shape mismatch')
    query_types=np.asarray(query_types)
    n=len(query_types); g=len(target.inputs.arrays['gene_names'])
    mean=np.zeros((g,n)); variance=np.broadcast_to(arrays['sigma2'][:,None],(g,n)).copy()
    flat=__import__('json').loads(target.identity).get('model')=='flat'
    for k in range(factors):
        if flat:
            w=np.asarray(query_locations)-target.inputs.arrays['slocs'].mean(axis=0)
        else:
            w=conditional_warp(target.geometry, arrays['W_active'][k],
                float(np.log(arrays['ell_U'][k])), float(arrays['sigma_U'][k]), query_projector, rng)
        fm,fv=conditional_factor(features(arrays['W_cell'][k],target.rule), arrays['eta'][k],
            features(w,target.rule),float(arrays['alpha'][k]),float(arrays['zeta'][k]))
        for c in range(arrays['loading'].shape[0]):
            rows=np.flatnonzero(query_types==c)
            lam=arrays['loading'][c,:,k]
            mean[:,rows]+=lam[:,None]*fm[rows]
            variance[:,rows]+=lam[:,None]**2*fv[rows]
    return mean,variance
