"""Selected F/C functions only; see docs/sampler/LAYER1_SOURCE_MAP.csv.

Validation precedes RNG consumption. Mathematical bodies and random calls are preserved.
"""
import numpy as np
from . import contracts


def compute_qgk(lambda_arr, s, Cn):
    """F/c3_established_functions.py:2817-2846; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.quadratic_inputs(lambda_arr, s, Cn)
    C, G, K = lambda_arr.shape
    qgk = np.zeros((G, K), dtype=np.float64)
    for k in range(K):
        sk = s[k]
        Lam_k = lambda_arr[:, :, k]
        sum_sq = np.sum(Lam_k ** 2, axis=0)
        sum_lam = np.sum(Lam_k, axis=0)
        if Cn == 1:
            qgk[:, k] = sum_sq
        else:
            denom = 1.0 - sk + C * sk
            qgk[:, k] = (sum_sq - sk * sum_lam ** 2 / denom) / (1.0 - sk)
    return qgk


def sample_phi(qgk, alpha, tau, Cn, G, K, a_phi=1.5, b_phi=1.5):
    """F/c3_established_functions.py:3886-3913; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.phi_inputs(qgk, alpha, tau, Cn, G, K, a_phi, b_phi)
    shape = a_phi + Cn / 2.0
    phi = np.zeros((G, K), dtype=np.float64)
    for k in range(K):
        rate = b_phi + alpha[k] ** 2 * tau[k] / 2.0 * qgk[:, k]
        phi[:, k] = np.random.gamma(shape, 1.0 / rate, size=G)
    return phi


def sample_delta_tau(qgk, alpha, phi, delta_prev, K, Cn, G, a_delta1=2.1, a_delta_gt1=1.5):
    """F/c3_established_functions.py:3859-3879; source SHA-256 828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946."""
    contracts.delta_inputs(qgk, alpha, phi, delta_prev, K, Cn, G, a_delta1, a_delta_gt1)
    alpha2 = alpha ** 2
    B = alpha2 * np.sum(phi * qgk, axis=0)
    delta = delta_prev.copy()
    tau = np.cumprod(delta)
    for j in range(K):
        a_j = a_delta1 if j == 0 else a_delta_gt1
        tau_over_dj = tau[j:] / delta[j]
        shape = a_j + 0.5 * G * Cn * (K - j)
        rate = 1.0 + 0.5 * np.sum(tau_over_dj * B[j:])
        delta[j] = np.random.gamma(shape, 1.0 / rate)
        tau = np.cumprod(delta)
    return (delta, tau)
