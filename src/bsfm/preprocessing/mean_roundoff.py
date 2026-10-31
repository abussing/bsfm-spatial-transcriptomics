"""Independent binary64 mean check; never changes stored means or responses."""
import math

import numpy as np

from .raw_preflight import require

MEAN_POLICY = {
    'schema': 'bsfm.mean-roundoff.v1',
    'reference': 'math.fsum_in_canonical_cell_order_divided_by_n',
    'unit_roundoff': 'float64_eps_divided_by_2',
    'writer_operation_bound': 'n',
    'reference_operation_bound': 'n',
    'safety_factor': 2.0,
}


def gamma_upper(k, u):
    """Upper-rounded gamma_k; k*u is exact for the supported integer sizes."""
    require(isinstance(k, int) and 1 <= k < 2**53 and k*u < 1, 'Unsupported summation length')
    denominator = math.nextafter(1.0-k*u, -math.inf)
    require(denominator > 0, 'Invalid roundoff denominator')
    return math.nextafter(k*u/denominator, math.inf)


def mean_allowance(n, mean_abs, policy):
    require(policy == MEAN_POLICY, 'Unreviewed mean roundoff policy')
    require(math.isfinite(mean_abs) and mean_abs >= 0, 'Invalid mean absolute magnitude')
    require(mean_abs == 0 or mean_abs >= np.finfo(np.float64).tiny, 'Subnormal mean outside roundoff model')
    u = float(np.finfo(np.float64).eps)/2
    writer_gamma = gamma_upper(n, u)
    # Conservative policy allocation, not a claimed sharp error theorem for fsum.
    reference_gamma = gamma_upper(n, u)
    if mean_abs == 0:
        return 0.0
    # Account for rounding in fsum(abs(x))/n as well as in both compared means.
    magnitude_upper = math.nextafter(mean_abs/math.nextafter(1-reference_gamma, -math.inf), math.inf)
    coefficient = math.nextafter(writer_gamma+reference_gamma, math.inf)
    bound = math.nextafter(coefficient*magnitude_upper, math.inf)
    bound = math.nextafter(policy['safety_factor']*bound, math.inf)
    require(math.isfinite(bound), 'Roundoff bound overflow')
    return bound


def check_means(chosen, types, stored, policy):
    """Reference order comes from already authenticated modeling columns, never sorted."""
    require(policy == MEAN_POLICY, 'Unreviewed mean roundoff policy')
    require(chosen.dtype == np.float64 and stored.dtype == np.float64, 'Means require binary64')
    require(chosen.ndim == 2 and types.shape == (chosen.shape[1],)
            and stored.shape == (chosen.shape[0], 3), 'Mean comparison shape mismatch')
    require(np.isfinite(chosen).all() and np.all(chosen >= 0) and np.isfinite(stored).all(),
            'Mean comparison requires finite nonnegative log1p responses')
    require(np.all((chosen == 0) | (chosen >= np.finfo(np.float64).tiny)), 'Subnormal response outside roundoff model')
    require(np.isin(types, [0, 1, 2]).all(), 'Unknown mean comparison group')
    reference = np.empty_like(stored); magnitude = np.empty_like(stored); bounds = np.empty_like(stored)
    sizes = []
    for t in range(3):
        indices = np.flatnonzero(types == t)
        n = len(indices); require(n > 0, 'Empty centering group'); sizes.append(n)
        for g in range(chosen.shape[0]):
            values = chosen[g, indices]
            reference[g, t] = math.fsum(values)/n
            magnitude[g, t] = math.fsum(abs(float(x)) for x in values)/n
            bounds[g, t] = mean_allowance(n, float(magnitude[g, t]), policy)
    require(np.isfinite(reference).all(), 'Reference mean overflow')
    discrepancy = np.abs(stored-reference)
    passed = discrepancy <= bounds
    require(bool(np.all(passed)), 'Centering means exceed forward-error bound')
    ratios = np.divide(discrepancy, bounds, out=np.zeros_like(bounds), where=bounds > 0)
    return {'policy': dict(policy), 'epsilon': float(np.finfo(np.float64).eps),
            'unit_roundoff': float(np.finfo(np.float64).eps)/2, 'group_sizes': sizes,
            'reference_means': reference.tolist(), 'mean_absolute_response': magnitude.tolist(),
            'absolute_discrepancies': discrepancy.tolist(), 'allowed_bounds': bounds.tolist(),
            'discrepancy_to_bound_ratios': ratios.tolist(),
            'comparison_pass': passed.tolist(), 'all_passed': True,
            'max_abs_discrepancy': float(discrepancy.max()), 'max_allowed_bound': float(bounds.max()),
            'max_discrepancy_to_bound_ratio': float(ratios.max())}
