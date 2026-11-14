"""Opt-in NUTS coordinates with original model positions at every public boundary.

Tuning masses, trajectory energies and momenta are in the policy's internal
coordinates. State positions/densities/gradients (including warmup history) are
converted back. Run receipts bind the policy, including its reference map.
"""
import copy
import blackjax
import jax
from .flat_control import FlatTarget, FlatTransition
from .layer5 import SplitTransition, TARGET_ACCEPTANCE, MAX_NUM_DOUBLINGS
from .reference_coordinates import build_reference_coordinates
from .split_kernels import make_logdensity, build_split
from .transition_policy import validate_transition_policy
from .variance_coordinates import to_variances, to_original, wrap_value_grad


def _original_boundaries(runner, target, encode, decode):
    ld = make_logdensity(target._kernels)

    def original_state(p, u, ct, penalty):
        return blackjax.nuts.init(decode(p), lambda q: ld(q, u, ct, penalty))

    @jax.jit
    def transition(key, p, u, ct, penalty, tuning):
        state, info = runner['transition'](key, encode(p), u, ct, penalty, tuning)
        return original_state(state.position, u, ct, penalty), info

    # Map sequentially: do not allocate a warmup-batch of feature covariances.
    convert_history = jax.jit(lambda positions, u, ct, penalty: jax.lax.map(
        lambda p: original_state(p, u, ct, penalty), positions))

    def adapt(key, p, u, ct, penalty, steps):
        (_, tuning), history = runner['adapt'](key, encode(p), u, ct, penalty, steps)
        states = convert_history(history.state.position, u, ct, penalty)
        history = history._replace(state=states)
        endpoint = jax.tree.map(lambda x: x[-1], states)
        return (endpoint, tuning), history

    return dict(transition=transition, adapt=adapt)


class _PolicyAudit:
    def _result(self, nuts_state, info, position, audit):
        audit.update(transition_policy=copy.deepcopy(self.policy),
                     trajectory_coordinates='transition_policy',
                     state_coordinates='original_model')
        return super()._result(nuts_state, info, position, audit)


class VarianceTransition(_PolicyAudit, FlatTransition):
    def __init__(self, target, policy):
        validate_transition_policy(policy, 'flat')
        super().__init__(target)
        self.policy = copy.deepcopy(policy)
        proxy = copy.copy(target)
        proxy._kernels = dict(target._kernels, value_grad=wrap_value_grad(target._kernels['value_grad']))
        runner = FlatTransition(proxy)._runner
        self._runner = _original_boundaries(runner, target, to_variances, to_original)


class ReferenceWarpTransition(_PolicyAudit, SplitTransition):
    def __init__(self, target, policy):
        validate_transition_policy(policy, 'deep')
        if isinstance(target, FlatTarget):
            raise ValueError('Reference warp requires a deep target')
        super().__init__(target)
        self.policy = copy.deepcopy(policy)
        chart = build_reference_coordinates(target._kernels, self.centered._kernels,
                                            self.dimension, policy['reference_warp'])
        runner = build_split(make_logdensity(chart), chart['maps'], self.dimension,
                             TARGET_ACCEPTANCE, MAX_NUM_DOUBLINGS)
        self._runner = _original_boundaries(runner, target, chart['to_reference'], chart['to_original'])


def policy_transition(target, policy):
    model = 'flat' if isinstance(target, FlatTarget) else 'deep'
    validate_transition_policy(policy, model)
    cls = VarianceTransition if model == 'flat' else ReferenceWarpTransition
    return cls(target, policy)
