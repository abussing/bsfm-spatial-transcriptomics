"""Selected F/C functions only; see docs/sampler/LAYER1_SOURCE_MAP.csv.

Validation precedes RNG consumption. Mathematical bodies and random calls are preserved.
"""
import numpy as np
from . import contracts
from scipy.linalg import cho_solve, solve_triangular


def compute_Yhat(lambda_arr, eta_mat, cell_slc):
    """F/c3_established_functions.py:2849-2869; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.fitted_inputs(lambda_arr, eta_mat, cell_slc)
    C, G, K = lambda_arr.shape
    N = eta_mat.shape[1]
    Yhat = np.zeros((G, N), dtype=np.float64)
    for c in range(C):
        slc = cell_slc[c]
        Yhat[:, slc] = lambda_arr[c] @ eta_mat[:, slc]
    return Yhat


def sample_Lambda_twostage(Y, eta_mat, sigma2, v, alpha, phi, tau, s, cell_slc):
    """F/c3_established_functions.py:6936-7026; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.lambda_inputs(Y, eta_mat, sigma2, v, alpha, phi, tau, s, cell_slc)
    Cn = len(cell_slc)
    G = Y.shape[0]
    K = eta_mat.shape[0]
    CK = Cn * K
    lambda_arr = np.zeros((Cn, G, K), dtype=np.float64)
    w = 1.0 / (sigma2[:, None] * v)
    Q_data_list = []
    b_data_list = []
    for c in range(Cn):
        slc = cell_slc[c]
        eta_c = eta_mat[:, slc]
        w_c = w[:, slc]
        Q_c = np.einsum('kn,gn,ln->gkl', eta_c, w_c, eta_c)
        b_c = np.einsum('kn,gn->gk', eta_c, w_c * Y[:, slc])
        Q_data_list.append(Q_c)
        b_data_list.append(b_c)
    Oinv_diag = np.zeros(K)
    Oinv_off = np.zeros(K)
    for k in range(K):
        sk = s[k]
        d = 1.0 - sk + Cn * sk
        Oinv_diag[k] = (1.0 - sk / d) / (1.0 - sk)
        Oinv_off[k] = -sk / d / (1.0 - sk)
    alpha2 = alpha ** 2
    for g in range(G):
        Q_g = np.zeros((CK, CK), dtype=np.float64)
        b_g = np.zeros(CK, dtype=np.float64)
        for c in range(Cn):
            blk = slice(c * K, (c + 1) * K)
            Q_g[blk, blk] += Q_data_list[c][g]
            b_g[blk] += b_data_list[c][g]
        for c in range(Cn):
            for cp in range(Cn):
                blk_c = slice(c * K, (c + 1) * K)
                blk_cp = slice(cp * K, (cp + 1) * K)
                if c == cp:
                    vals = alpha2 * phi[g, :] * tau * Oinv_diag
                else:
                    vals = alpha2 * phi[g, :] * tau * Oinv_off
                Q_g[blk_c, blk_cp] += np.diag(vals)
        L_g = np.linalg.cholesky(Q_g)
        mu_g = cho_solve((L_g, True), b_g)
        z = np.random.standard_normal(CK)
        ell_g = mu_g + solve_triangular(L_g.T, z, lower=False)
        for c in range(Cn):
            lambda_arr[c, g, :] = ell_g[c * K:(c + 1) * K]
    return lambda_arr


def sample_sigma2_twostage(Y, Yhat, v, a_sigma, b_sigma):
    """F/c3_established_functions.py:7193-7216; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.noise_inputs(Y, Yhat, v, a_sigma, b_sigma)
    G, N = Y.shape
    resid = Y - Yhat
    weighted_rss = np.sum(resid ** 2 / v, axis=1)
    n_eff = np.sum(1.0 / v, axis=1)
    shape = a_sigma + n_eff / 2.0
    rate = np.asarray(b_sigma) + weighted_rss / 2.0
    return 1.0 / np.random.gamma(shape, 1.0 / rate, size=G)
