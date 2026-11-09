"""Explicit recipe for independent stationary factor ranges, in tissue units."""
import math


def validate_range_prior(prior):
    if not isinstance(prior, dict) or set(prior) != {'median', 'log_sd', 'initial'}:
        raise ValueError('Flat range prior requires median, log_sd and initial')
    if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0
           for x in prior.values()):
        raise ValueError('Flat range prior parameters must be positive finite numbers')
    variance = float(prior['log_sd']) * float(prior['log_sd'])
    if not math.isfinite(variance) or variance <= 0:
        raise ValueError('Flat log-range prior variance must be representable')
    return {key: float(prior[key]) for key in ('median', 'log_sd', 'initial')}
