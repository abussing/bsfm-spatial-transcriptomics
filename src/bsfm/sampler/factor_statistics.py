"""Selected current-factor statistics and exact conditional draw kernels."""
import numpy as np
from .shrinkage import compute_qgk

def sufficient_statistics(y, yhat, loading, eta, sigma2, factor, cell_id):
    """Established C3 collapsed-factor u and ctilde."""
    y = np.asarray(y, float)
    yhat = np.asarray(yhat, float)
    loading = np.asarray(loading, float)
    eta = np.asarray(eta, float)
    precision = 1.0 / np.asarray(sigma2, float)
    n = y.shape[1]
    u = np.empty(n, float)
    ct = np.empty(n, float)
    for c in range(loading.shape[0]):
        rows = np.flatnonzero(cell_id == c)
        lam = loading[c, :, factor]
        residual_without = y[:, rows] - yhat[:, rows] + lam[:, None] * eta[factor, rows][None, :]
        u[rows] = np.sum(lam * lam * precision)
        ct[rows] = lam @ (precision[:, None] * residual_without)
    return (u, ct)

def sample_single_eta(rng, *, features, alpha, zeta, u, ct):
    """Exact eta_k conditional in the separate-(Lambda,alpha) model."""
    features = np.asarray(features, float)
    u = np.asarray(u, float)
    ct = np.asarray(ct, float)
    alpha = float(alpha)
    zeta = float(zeta)
    nugget_variance = alpha * alpha * (1.0 - zeta)
    smooth_variance = alpha * alpha * zeta
    denominator = 1.0 + nugget_variance * u
    weight = u / denominator
    sufficient = ct / denominator
    columns = features.shape[1]
    hessian = np.eye(columns) + smooth_variance * (features.T @ (weight[:, None] * features))
    chol = np.linalg.cholesky(hessian)
    rhs = np.sqrt(smooth_variance) * (features.T @ sufficient)
    mean_beta = np.linalg.solve(chol.T, np.linalg.solve(chol, rhs))
    beta = mean_beta + np.linalg.solve(chol.T, rng.standard_normal(columns))
    smooth = np.sqrt(smooth_variance) * (features @ beta)
    nugget_sd = np.sqrt(nugget_variance)
    xi_mean = nugget_sd * (ct - u * smooth) / denominator
    xi = xi_mean + rng.standard_normal(len(u)) / np.sqrt(denominator)
    return smooth + nugget_sd * xi

def factor_context(y, yhat, loading, eta, sigma2, phi, tau, s, factor, cell_id):
    u, ct = sufficient_statistics(y, yhat, loading, eta, sigma2, factor, cell_id)
    qgk = compute_qgk(loading, s, loading.shape[0])
    penalty = float(tau[factor] * np.sum(phi[:, factor] * qgk[:, factor]))
    return (u, ct, penalty)
