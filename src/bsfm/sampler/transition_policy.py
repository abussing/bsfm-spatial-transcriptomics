"""Explicit computational coordinates; these do not select a different model."""
import math


def validate_transition_policy(policy, model):
    if not isinstance(policy, dict):
        raise ValueError('Explicit transition policy object required')
    if model == 'flat' and policy == {'name': 'flat_variances_v1'}:
        return
    if (model == 'deep' and set(policy) == {'name', 'reference_warp'}
            and policy['name'] == 'deep_reference_warp_v1'):
        ref = policy['reference_warp']
        if (isinstance(ref, list) and len(ref) == 2
                and all(type(x) in (int, float) and math.isfinite(x) for x in ref)):
            return
    raise ValueError('Unknown or model-incompatible transition policy')
