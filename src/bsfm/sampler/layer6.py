"""One identity-bound C3 Gibbs sweep; no runner, adaptation or checkpoint.

All numerical updates come from accepted Layers 1-5. Caller state is copied;
RNG streams are intentionally not rolled back if an operation fails.
"""
import copy
from dataclasses import dataclass
import hashlib
import json

import jax
import jax.numpy as jnp
import numpy as np

from . import contracts
from .conjugate import compute_Yhat, sample_Lambda_twostage, sample_sigma2_twostage
from .shrinkage import compute_qgk, sample_phi, sample_delta_tau
from .px import refresh_alpha_gauge
from .field_target import FieldPosition
from .chart import validate_chart_state
from .layer4 import STATE_ARRAYS, state_hashes, JointEtaConditional
from .layer5 import SplitTransition

N_INNER = 3
SIGMA2_PRIOR_SHAPE = 2.0
ELL_ETA = .14


def _json_value(x):
    if isinstance(x, np.ndarray):
        return dict(dtype=x.dtype.str, shape=list(x.shape), values=x.tolist())
    if isinstance(x, np.generic):
        return x.item()
    raise TypeError(type(x).__name__)


def _digest(x):
    return hashlib.sha256(json.dumps(x, default=_json_value, sort_keys=True,
                                    allow_nan=False, separators=(',', ':')).encode()).hexdigest()


def rng_audit(eta_rng, gauge_rng, master_key):
    """Stream identities only, not a serializable restart checkpoint."""
    return dict(numpy_global_sha256=_digest(np.random.get_state()),
                eta_generator=type(eta_rng.bit_generator).__name__,
                eta_rng_sha256=_digest(eta_rng.bit_generator.state),
                gauge_generator=type(gauge_rng.bit_generator).__name__,
                gauge_rng_sha256=_digest(gauge_rng.bit_generator.state),
                jax_impl=str(jax.random.key_impl(master_key)),
                jax_key_data=np.asarray(jax.random.key_data(master_key)).tolist())


@dataclass(frozen=True)
class SweepResult:
    state: contracts.GaussianState
    positions: tuple
    master_key: object
    factor_order: tuple
    pcg_diagnostics: tuple
    px_audit: dict
    factor_diagnostics: tuple
    warp_summaries: tuple
    fitted_Y: np.ndarray
    audit: dict


class GibbsSweep:
    """Compose one sweep with frozen factor tuning and caller-owned RNGs.

    The global np.random stream is historical, so concurrent chains in one
    process are not safe. Invalid inputs fail before RNG draws; numerical
    failures may advance streams but never return a partial SweepResult.
    """
    def __init__(self, target, *, b_sigma2):
        self.split = SplitTransition(target)
        self.joint_eta = JointEtaConditional(target)
        self.target = target
        y = target.inputs.arrays['Y']
        # Authenticate the supplied fixed initialization scale, never estimate
        # or replace it. Layer 1 retains its .25*var(Y) validation requirement.
        contracts.noise_inputs(y, np.zeros_like(y), np.ones_like(y),
                               SIGMA2_PRIOR_SHAPE, b_sigma2)
        self._b_sigma2 = np.array(b_sigma2, copy=True)
        self._b_sigma2.flags.writeable = False
        self._prior_hash = contracts.logical_hash(self._b_sigma2)

    def _validate(self, state, positions, tuning, eta_rng, gauge_rng, master_key,
                  state_factor_ids, label):
        if (self.target is not self.split.target or self.target is not self.joint_eta.target
                or not isinstance(state, contracts.GaussianState)):
            raise ValueError('Sweep target/state binding mismatch')
        k = len(self.target.factor_ids)
        if not isinstance(positions, tuple) or len(positions) != k:
            raise ValueError('One position per ordered factor required')
        if not isinstance(tuning, tuple) or len(tuning) != k:
            raise ValueError('One frozen tuning per ordered factor required')
        for i, (p, t) in enumerate(zip(positions, tuning)):
            validate_chart_state(self.target, p, state, i)
            self.split.validate_inputs(master_key, p, state, t, state_factor_ids=state_factor_ids)
        if (not isinstance(eta_rng, np.random.Generator)
                or not isinstance(gauge_rng, np.random.Generator)
                or eta_rng.bit_generator is gauge_rng.bit_generator):
            raise ValueError('Distinct explicit eta and gauge Generators required')
        if not isinstance(label, str) or not label:
            raise ValueError('Explicit nonempty sweep audit label required')
        if contracts.logical_hash(self._b_sigma2) != self._prior_hash:
            raise ValueError('Frozen initialization noise scale changed')

    def _joint_eta(self, positions, state, rng):
        eta, _, diag, _ = self.joint_eta.draw(
            positions, state, rng, state_factor_ids=self.target.factor_ids)
        return eta, diag

    def sweep(self, state, positions, tuning, *, eta_rng, gauge_rng, master_key,
              state_factor_ids, label, observer=None):
        if observer is not None and not callable(observer):
            raise TypeError("observer must be callable")
        self._validate(state, positions, tuning, eta_rng, gauge_rng, master_key,
                       state_factor_ids, label)
        before = rng_audit(eta_rng, gauge_rng, master_key)
        input_hashes = state_hashes(state)
        position_hashes = [contracts.logical_hash(p.values) for p in positions]
        work = copy.deepcopy(state)
        current = [FieldPosition(np.array(p.values, copy=True), p.factor_id,
                                 p.target_identity) for p in positions]
        target = self.target
        k = len(target.factor_ids)
        y = target.inputs.arrays['Y']
        c = len(target.inputs.arrays['cell_type_names'])
        g = y.shape[0]
        cell_slices = work.validate(target.inputs, factors=k)
        v = np.ones_like(y)
        sharing = np.full(k, contracts.SHARING)
        def observe(event, **details):
            # Audit only: detached snapshots, no access to the live RNG objects.
            # The observer must not use global RNGs or mutate external state.
            if observer is not None:
                observer(event, copy.deepcopy(work), tuple(
                    FieldPosition(np.array(p.values, copy=True), p.factor_id,
                                  p.target_identity) for p in current), copy.deepcopy(details))

        pcgs = []
        observe('sweep_start')
        for _inner in range(N_INNER):
            work.loading = sample_Lambda_twostage(
                y, work.eta, work.sigma2, v, work.alpha, work.phi, work.tau,
                sharing, cell_slices)
            observe('after_loading', inner=_inner)
            work.eta, pcg = self._joint_eta(tuple(current), work, eta_rng)
            pcgs.append(pcg)
            observe('after_joint_eta', inner=_inner, pcg=pcg)
            yhat = compute_Yhat(work.loading, work.eta, cell_slices)
            work.sigma2 = sample_sigma2_twostage(
                y, yhat, v, SIGMA2_PRIOR_SHAPE, self._b_sigma2)
            observe('after_noise', inner=_inner)

        qgk = compute_qgk(work.loading, sharing, c)
        work.phi = sample_phi(qgk, work.alpha, work.tau, c, g, k,
                             a_phi=contracts.A_PHI, b_phi=contracts.B_PHI)
        observe('after_phi')
        work.delta, work.tau = sample_delta_tau(
            qgk, work.alpha, work.phi, work.delta, k, c, g,
            a_delta1=contracts.A_DELTA1, a_delta_gt1=contracts.A_DELTA_LATER)
        observe('after_delta_tau')
        work.loading, work.eta, work.alpha, gauge = refresh_alpha_gauge(
            work.loading, work.eta, work.alpha, gauge_rng, sharing, label)
        for i in range(k):
            current[i].values[0] = np.log(work.alpha[i])
        observe('after_px')
        yhat = compute_Yhat(work.loading, work.eta, cell_slices)

        order = tuple(int(i) for i in np.random.permutation(k))
        factors = []
        warp = [None]*k
        for i in order:
            observe('before_factor', factor_index=i)
            # Rebuild current Yhat/context before the historical key split.
            context = self.split.prepare_context(current[i], work,
                                                 state_factor_ids=target.factor_ids)
            master_key, step_key = jax.random.split(master_key)
            result = self.split.transition(step_key, current[i], work, tuning[i],
                state_factor_ids=target.factor_ids, prepared_context=context)
            current[i] = result.position
            p = current[i].values
            work.alpha[i] = float(np.exp(np.asarray(p[0])))
            work.zeta[i] = float(jax.nn.sigmoid(jnp.asarray(p[1])))
            warp[i] = dict(factor_id=target.factor_ids[i], **target.hyperparameters(current[i]))
            observe('after_factor_transition', factor_index=i)
            # Layer 3 reuses the same u/ct: alpha/zeta changes do not enter
            # those statistics, and no eta changes before this one draw.
            work.eta[i], eta_audit = target.draw_eta(
                current[i], work, eta_rng, state_factor_ids=target.factor_ids)
            for name in ('u_sha256', 'ct_sha256'):
                if eta_audit[name] != result.audit['context'][name]:
                    raise RuntimeError('Post-transition eta context changed before draw')
            yhat = compute_Yhat(work.loading, work.eta, cell_slices)
            observe('after_single_eta', factor_index=i)
            factors.append(dict(factor_index=i, factor_id=target.factor_ids[i],
                                transition=result, eta_audit=eta_audit))

        work.validate(target.inputs, factors=k)
        target._validate_identities()
        for i, p in enumerate(current):
            validate_chart_state(target, p, work, i)
            p.values.flags.writeable = False
        for row in warp:
            if not all(np.isfinite(row[n]) and row[n] > 0 for n in ('ell_eta', 'ell_W', 'sigma_W')):
                raise RuntimeError('Invalid derived warp summary')
        audit = dict(schema='bsfm.completed-sweep-audit.v1', label=label,
                     target_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),
                     factor_ids=list(target.factor_ids), b_sigma2_sha256=self._prior_hash,
                     state_before=input_hashes, state_after=state_hashes(work),
                     positions_before=position_hashes,
                     positions_after=[contracts.logical_hash(p.values) for p in current],
                     rng_before=before, rng_after=rng_audit(eta_rng, gauge_rng, master_key),
                     fitted_Y_sha256=contracts.logical_hash(yhat))
        return SweepResult(work, tuple(current), master_key, order, tuple(pcgs),
                           gauge, tuple(factors), tuple(warp), yhat, audit)
