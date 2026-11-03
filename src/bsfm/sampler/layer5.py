"""Identity-bound split field/hyper NUTS and window adaptation only.

No eta draw or GaussianState mutation. Caller owns key advancement and later
Gibbs updates. Fixed kernels are cached; conditional statistics are rebuilt.
"""
from dataclasses import dataclass
import importlib.metadata
import json
import os
from weakref import WeakKeyDictionary

import jax
import jax.numpy as jnp
import numpy as np

from .contracts import array, logical_hash
from .chart import validate_chart_state
from .field_target import FieldPosition
from .layer4 import _Binding, CenteredHyperTarget
from .split_kernels import build_split, make_logdensity

TARGET_ACCEPTANCE = .9
MAX_NUM_DOUBLINGS = 10
INITIAL_STEP_SIZE = .01
MIN_ADAPTATION_STEPS = 20
PHYSICAL_W_RELATIVE_TOLERANCE = 2e-8


@dataclass(frozen=True)
class SplitTuning:
    target_identity: str
    factor_id: str
    step_size: float
    hyper_step_size: float
    inverse_mass_matrix: np.ndarray
    mass_sha256: str


@dataclass(frozen=True)
class SplitResult:
    position: FieldPosition
    nuts_state: object
    info: object
    audit: dict


@dataclass(frozen=True)
class AdaptationResult:
    endpoint: SplitResult
    tuning: SplitTuning
    history: object


@dataclass(frozen=True, eq=False)
class PreparedContext:
    """Process-local conditional issued by one SplitTransition, not a cache file.

    Arrays have immutable byte backing. The issuer also authenticates identity
    and contents; constructing or replacing a record does not issue it.
    """
    u: np.ndarray
    ct: np.ndarray
    penalty: float
    context_json: str
    position_sha256: str


class SplitTransition(_Binding):
    """Canonical two-block transition, using explicit fresh caller state."""
    def __init__(self, target):
        super().__init__(target)
        if importlib.metadata.version('blackjax') != '1.3':
            raise ValueError('BlackJAX 1.3 required')
        if jax.default_backend() != 'cpu':
            if not (jax.default_backend() == 'gpu' and jax.config.x64_enabled
                    and os.environ.get('BSFM_EXPERIMENTAL_CUDA') == '1'):
                raise ValueError('Non-CPU execution requires explicit experimental CUDA/x64 opt-in')
        self.dimension = 4 + 2*len(target.geometry.arrays['active_indices'])
        self.centered = CenteredHyperTarget(target)
        self._runner = build_split(make_logdensity(target._kernels),
                                  self.centered._kernels, self.dimension,
                                  TARGET_ACCEPTANCE, MAX_NUM_DOUBLINGS)
        self._prepared = WeakKeyDictionary()

    def _key(self, key):
        try:
            data = np.asarray(jax.random.key_data(key))
            impl = str(jax.random.key_impl(key))
        except (TypeError, ValueError) as exc:
            raise ValueError('Explicit scalar JAX threefry2x32 key required') from exc
        if data.shape != (2,) or data.dtype != np.uint32 or impl != 'threefry2x32':
            raise ValueError('Explicit scalar JAX threefry2x32 key required')
        return data.tolist()

    def _state_position(self, position, state, state_factor_ids):
        self._check(state, state_factor_ids)
        self.target._check_position(position)
        k = self.target.factor_ids.index(position.factor_id)
        validate_chart_state(self.target, position, state, k)

    def validate_inputs(self, key, position, state, tuning, *, state_factor_ids):
        """Authenticate a transition boundary without context building or RNG."""
        self._state_position(position, state, state_factor_ids)
        self._key(key)
        self._tuning(tuning, position.factor_id)

    @staticmethod
    def _context_signature(prepared):
        return (prepared.context_json, prepared.position_sha256,
                logical_hash(prepared.u), logical_hash(prepared.ct),
                logical_hash(np.asarray(prepared.penalty)))

    def prepare_context(self, position, state, *, state_factor_ids):
        """Bind current statistics before the caller advances its master key."""
        self._state_position(position, state, state_factor_ids)
        u, ct, penalty, context = self.target.context(
            state, factor_id=position.factor_id, state_factor_ids=state_factor_ids)
        def freeze(x):
            a = np.asarray(x)
            return np.frombuffer(a.tobytes(), dtype=a.dtype).reshape(a.shape)
        prepared = PreparedContext(freeze(u), freeze(ct), penalty,
            json.dumps(context, sort_keys=True, allow_nan=False), logical_hash(position.values))
        self._prepared[prepared] = self._context_signature(prepared)
        return prepared

    def _consume_context(self, prepared, position, state):
        if (not isinstance(prepared, PreparedContext) or prepared not in self._prepared
                or self._prepared[prepared] != self._context_signature(prepared)):
            raise ValueError('Unissued, foreign or changed prepared context')
        context = json.loads(prepared.context_json)
        record = self._record(state)
        if (context['target_sha256'] != record['target_sha256']
                or context['factor_id'] != position.factor_id
                or context['state_array_hashes'] != record['state_array_hashes']
                or prepared.position_sha256 != logical_hash(position.values)
                or context['u_sha256'] != logical_hash(prepared.u)
                or context['ct_sha256'] != logical_hash(prepared.ct)
                or context['penalty'] != prepared.penalty):
            raise ValueError('Stale prepared context: state, position or identity changed')
        return prepared.u, prepared.ct, prepared.penalty, context

    def _inputs(self, key, position, state, state_factor_ids, prepared_context=None):
        self._state_position(position, state, state_factor_ids)
        key_data = self._key(key)
        if prepared_context is None:
            prepared_context = self.prepare_context(position, state, state_factor_ids=state_factor_ids)
        u, ct, penalty, context = self._consume_context(prepared_context, position, state)
        audit = self._record(state)
        audit.update(context=context, input_position_sha256=logical_hash(position.values),
                     key_data=key_data, eta_redrawn=False,
                     key_policy='Caller supplies one key; no next key returned or implicit advancement')
        return tuple(map(jnp.asarray, (position.values, u, ct, penalty))), audit

    def tuning(self, factor_id, *, step_size=INITIAL_STEP_SIZE,
               hyper_step_size=INITIAL_STEP_SIZE, inverse_mass_matrix=None):
        """Freeze tuning; defaults are initial mechanics, not learned tuning."""
        if inverse_mass_matrix is None:
            inverse_mass_matrix = np.ones(self.dimension, dtype=np.float64)
        mass = np.array(inverse_mass_matrix, copy=True)
        mass.flags.writeable = False
        result = SplitTuning(self.target_identity, factor_id, step_size,
                             hyper_step_size, mass, logical_hash(mass))
        self._tuning(result, factor_id)
        return result

    def _tuning(self, tuning, factor_id):
        if (not isinstance(tuning, SplitTuning)
                or tuning.target_identity != self.target_identity
                or tuning.factor_id != factor_id or factor_id not in self.target.factor_ids):
            raise ValueError('Tuning target/factor binding mismatch')
        for x in (tuning.step_size, tuning.hyper_step_size):
            if np.ndim(x) != 0 or isinstance(x, (bool, np.bool_)) or not np.isfinite(x) or x <= 0:
                raise ValueError('Positive finite scalar step sizes required')
        array(tuning.inverse_mass_matrix, 'diagonal inverse mass', (self.dimension,), positive=True)
        if logical_hash(tuning.inverse_mass_matrix) != tuning.mass_sha256:
            raise ValueError('Tuning mass mutated')
        return dict(step_size=jnp.asarray(tuning.step_size),
                    hyper_step_size=jnp.asarray(tuning.hyper_step_size),
                    inverse_mass_matrix=jnp.asarray(tuning.inverse_mass_matrix))

    def _validate_info(self, info):
        error = np.asarray(info.hyper_W_relative_error)
        if not np.isfinite(error).all() or np.any(error >= PHYSICAL_W_RELATIVE_TOLERANCE):
            raise RuntimeError('Split fixed-physical-W relative invariant failed')
        ac = np.asarray(info.block_acceptance)
        if ac.shape[-1:] != (2,) or not np.isfinite(ac).all() or np.any((ac < 0) | (ac > 1)):
            raise RuntimeError('Invalid block acceptance diagnostics: '+repr(ac.tolist()))
        # A divergent trajectory stays visible; it is not silently retried.
        # Nonfinite trajectory energy is allowed only for that divergent block.
        energy = np.asarray(info.block_energy)
        divergent = np.asarray(info.block_divergent)
        if np.any(~np.isfinite(energy) & ~divergent):
            raise RuntimeError('Nonfinite nondivergent block energy')

    def _result(self, nuts_state, info, position, audit):
        self._validate_info(info)
        values = np.array(nuts_state.position)
        result = FieldPosition(values, position.factor_id, self.target_identity)
        self.target._check_position(result)
        if not np.isfinite(nuts_state.logdensity) or not np.isfinite(nuts_state.logdensity_grad).all():
            raise RuntimeError('Nonfinite split endpoint')
        values.flags.writeable = False
        audit.update(output_position_sha256=logical_hash(values),
                     maximum_W_relative_error=float(np.max(np.asarray(info.hyper_W_relative_error))),
                     W_relative_tolerance=PHYSICAL_W_RELATIVE_TOLERANCE)
        return SplitResult(result, nuts_state, info, audit)

    def transition(self, key, position, state, tuning, *, state_factor_ids, prepared_context=None):
        args, audit = self._inputs(key, position, state, state_factor_ids, prepared_context)
        tuned = self._tuning(tuning, position.factor_id)
        nuts_state, info = self._runner['transition'](key, *args, tuned)
        return self._result(nuts_state, info, position, audit)

    def adapt(self, key, position, state, *, state_factor_ids, steps):
        if isinstance(steps, (bool, np.bool_)) or not isinstance(steps, (int, np.integer)) or steps < MIN_ADAPTATION_STEPS:
            raise ValueError('Split window adaptation requires an integer >=20')
        args, audit = self._inputs(key, position, state, state_factor_ids)
        (nuts_state, raw_tuning), history = self._runner['adapt'](key, *args, int(steps))
        self._validate_info(history.info)
        tuning = self.tuning(position.factor_id, step_size=float(raw_tuning['step_size']),
                             hyper_step_size=float(raw_tuning['hyper_step_size']),
                             inverse_mass_matrix=np.asarray(raw_tuning['inverse_mass_matrix']))
        if not np.array_equal(nuts_state.position, np.asarray(history.state.position)[-1]):
            raise RuntimeError('Warmup endpoint did not propagate')
        final_info = jax.tree.map(lambda x: x[-1], history.info)
        audit.update(adaptation_steps=int(steps),
                     maximum_warmup_W_relative_error=float(np.max(history.info.hyper_W_relative_error)))
        endpoint = self._result(nuts_state, final_info, position, audit)
        return AdaptationResult(endpoint, tuning, history)
