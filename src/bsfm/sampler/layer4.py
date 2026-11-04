"""Authenticated fixed-physical-W target and joint-eta conditional draw.

No hyperparameter transition, adaptation, sweep, or checkpoint is implemented.
Numerical kernels retain the selected F arithmetic; this boundary binds them to
the accepted input/state, geometry, frozen rule and ordered factor identities.
"""
from dataclasses import dataclass, asdict
import hashlib
import json

import jax.numpy as jnp
import numpy as np

from .contracts import array, logical_hash
from .chart import validate_chart_state
from .field_target import DirectWTarget
from .centered_hyper_kernels import build_centered_hyper_target
from .joint_eta_kernels import sample_joint_eta_pcg
from .warp import PHYSICAL_W_TOLERANCE, _parameters

POSTERIOR_RMS_TOLERANCE = 1e-10
MAXIMUM_PCG_ITERATIONS = 80
STATE_ARRAYS = ('loading', 'eta', 'alpha', 'zeta', 'sigma2', 'phi', 'delta', 'tau')


def state_hashes(state):
    return {name: logical_hash(getattr(state, name)) for name in STATE_ARRAYS}


class _Binding:
    def __init__(self, target):
        if not isinstance(target, DirectWTarget):
            raise ValueError('An authenticated DirectWTarget is required')
        target._validate_identities()
        self.target = target
        self.target_identity = target.identity

    def _check(self, state, state_factor_ids):
        self.target._validate_identities()
        if (self.target.identity != self.target_identity
                or state_factor_ids != self.target.factor_ids):
            raise ValueError('Layer-4 input/geometry/rule/factor binding mismatch')
        state.validate(self.target.inputs, factors=len(self.target.factor_ids))

    def _record(self, state):
        return dict(target_sha256=hashlib.sha256(self.target_identity.encode()).hexdigest(),
                    factor_ids=list(self.target.factor_ids), state_array_hashes=state_hashes(state))


@dataclass(frozen=True)
class FixedPhysicalField:
    values: np.ndarray
    factor_id: str
    target_identity: str
    values_sha256: str


class CenteredHyperTarget(_Binding):
    """Conditional density in dx db at fixed physical active W, two columns."""
    def __init__(self, target):
        super().__init__(target)
        g = target.geometry
        self._kernels = build_centered_hyper_target(
            g.spectral['U'][g.arrays['active_indices']], g.spectral)

    def _parameters(self, xb):
        array(xb, 'log_ell/log_r', (2,))
        _parameters(xb[0], xb[1])

    def freeze(self, position, state, *, state_factor_ids):
        self._check(state, state_factor_ids)
        self.target._check_position(position)
        xb = position.values[2:4]
        self._parameters(xb)
        w = np.array(self._kernels['physical'](jnp.asarray(xb),
                         jnp.asarray(position.values[4:].reshape(-1, 2))))
        array(w, 'physical active W', (len(self.target.geometry.arrays['active_indices']), 2))
        w.flags.writeable = False
        return FixedPhysicalField(w, position.factor_id, self.target_identity, logical_hash(w))

    def _field(self, field):
        if (not isinstance(field, FixedPhysicalField)
                or field.target_identity != self.target_identity
                or field.factor_id not in self.target.factor_ids):
            raise ValueError('Fixed physical field identity mismatch')
        array(field.values, 'physical active W', (len(self.target.geometry.arrays['active_indices']), 2))
        if logical_hash(field.values) != field.values_sha256:
            raise ValueError('Fixed physical field mutated')

    def value_grad(self, xb, field, state, *, state_factor_ids):
        self._check(state, state_factor_ids); self._parameters(xb); self._field(field)
        value, gradient = self._kernels['value_grad'](jnp.asarray(xb), jnp.asarray(field.values))
        if not np.isfinite(value) or not np.isfinite(gradient).all():
            raise RuntimeError('Nonfinite fixed-W conditional; no jitter or fallback')
        record = self._record(state)
        record.update(factor_id=field.factor_id, W_active_sha256=field.values_sha256)
        return float(value), np.asarray(gradient), record

    def rewhiten(self, xb, field, state, *, state_factor_ids):
        """Inverse chart only; caller owns any later accept/reject decision."""
        self._check(state, state_factor_ids); self._parameters(xb); self._field(field)
        z = np.asarray(self._kernels['whiten'](jnp.asarray(xb), jnp.asarray(field.values)))
        restored = np.asarray(self._kernels['physical'](jnp.asarray(xb), jnp.asarray(z)))
        error = float(np.max(np.abs(restored-field.values)))
        if not np.isfinite(z).all() or not np.isfinite(error) or error > PHYSICAL_W_TOLERANCE:
            raise RuntimeError('Fixed-W rewhitening invariant failed')
        return z, dict(max_absolute_error=error, tolerance=PHYSICAL_W_TOLERANCE,
                       W_active_sha256=field.values_sha256, factor_id=field.factor_id,
                       target_sha256=hashlib.sha256(self.target_identity.encode()).hexdigest())


class JointEtaConditional(_Binding):
    """Return one all-factor draw without mutating any GaussianState array."""
    def draw(self, positions, state, rng, *, state_factor_ids):
        self._check(state, state_factor_ids)
        if not isinstance(rng, np.random.Generator):
            raise ValueError('Explicit NumPy Generator required; no JAX key/reseeding')
        if not isinstance(positions, tuple) or len(positions) != len(self.target.factor_ids):
            raise ValueError('One position per ordered factor required')
        for k, pos in enumerate(positions):
            validate_chart_state(self.target, pos, state, k)
        features = np.stack([self.target.features(pos)[2] for pos in positions])
        feature_columns = 2 * self.target.rule.arrays['omega'].shape[0]
        shape = (len(positions), self.target.inputs.arrays['Y'].shape[1], feature_columns)
        array(features, 'canonical finite features', shape)
        record = self._record(state)
        record.update(features_sha256=logical_hash(features),
                      position_hashes=[logical_hash(p.values) for p in positions],
                      rng_before=json.loads(json.dumps(rng.bit_generator.state, default=lambda x: x.tolist())))
        eta, beta, diagnostics = sample_joint_eta_pcg(
            rng, y=self.target.inputs.arrays['Y'], loading=state.loading,
            alpha=state.alpha, sigma2=state.sigma2,
            cell_id=self.target.inputs.arrays['cell_id'], zeta=state.zeta,
            features=features, tolerance=POSTERIOR_RMS_TOLERANCE,
            maximum_iterations=MAXIMUM_PCG_ITERATIONS)
        array(eta, 'joint eta draw', state.eta.shape)
        array(beta, 'feature coefficients', (len(positions), feature_columns))
        if (not diagnostics.converged
                or not np.isfinite(list(asdict(diagnostics).values())).all()
                or diagnostics.posterior_mahalanobis_RMS_error_upper_bound > POSTERIOR_RMS_TOLERANCE):
            raise RuntimeError('Joint eta numerical contract failed; no partial update')
        record['rng_after'] = json.loads(json.dumps(rng.bit_generator.state, default=lambda x: x.tolist()))
        return eta, beta, diagnostics, record
