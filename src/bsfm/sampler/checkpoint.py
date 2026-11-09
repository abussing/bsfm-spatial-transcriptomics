"""Complete sweep-boundary NPZ checkpoints; no runner or legacy conversion."""
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np

from .contracts import GaussianState, array, logical_hash
from .conjugate import compute_Yhat
from .field_target import FieldPosition
from .layer4 import STATE_ARRAYS, state_hashes
from .layer5 import SplitTransition, SplitTuning
from .layer6 import SweepResult
from .checkpoint_contract import (SCHEMA, CheckpointContract, build_checkpoint_contract,
                                  validate_contract, validate_progress, digest)
from .checkpoint_rng import (json_text, parse_json, exact_keys, generator_record,
    restore_generator, global_record, restore_global, key_record, restore_key, stream_audit)


@dataclass(frozen=True)
class RestartState:
    state: GaussianState
    positions: tuple
    tuning: tuple
    eta_rng: object
    gauge_rng: object
    numpy_global_state: tuple
    master_key: object
    b_sigma2: np.ndarray
    progress: dict
    contract: CheckpointContract
    boundary: dict
    logical_sha256: str


class CheckpointWriteError(RuntimeError):
    def __init__(self, temporary_path):
        self.temporary_path = Path(temporary_path)
        super().__init__('Checkpoint not promoted; failed attempt retained at '+str(temporary_path))


def _descriptor(a):
    if not isinstance(a, np.ndarray) or a.dtype.hasobject:
        raise ValueError('Checkpoint arrays must be non-object ndarrays')
    return dict(dtype=a.dtype.str, shape=list(a.shape), sha256=logical_hash(a),
                fortran_order=bool(a.flags.f_contiguous and not a.flags.c_contiguous))


def _boundary(state, positions, target, b_sigma2, rng, label):
    slices = state.validate(target.inputs, factors=len(target.factor_ids))
    return dict(state_after=state_hashes(state), positions_after=[logical_hash(p.values) for p in positions],
        target_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),
        b_sigma2_sha256=logical_hash(b_sigma2), rng_after=rng, label=label,
        fitted_Y_sha256=logical_hash(compute_Yhat(state.loading, state.eta, slices)))


def _payload(target, contract, result, tuning, eta_rng, gauge_rng, b_sigma2, progress):
    contract_record = validate_contract(contract, target, b_sigma2)
    if not isinstance(result, SweepResult) or not isinstance(tuning, tuple):
        raise ValueError('Completed SweepResult and ordered frozen tuning required')
    if eta_rng is gauge_rng or eta_rng.bit_generator is gauge_rng.bit_generator:
        raise ValueError('Eta and gauge streams must be distinct')
    global_state = np.random.get_state()
    streams = stream_audit(eta_rng, gauge_rng, result.master_key, global_state)
    boundary = _boundary(result.state, result.positions, target, b_sigma2, streams, result.audit['label'])
    if (result.audit.get('schema') != 'bsfm.completed-sweep-audit.v1'
            or result.audit.get('factor_ids') != list(target.factor_ids)
            or any(result.audit.get(k) != v for k, v in boundary.items())
            or logical_hash(result.fitted_Y) != boundary['fitted_Y_sha256']):
        raise ValueError('State/positions/RNG no longer match a completed coherent sweep')
    data = {name: np.array(getattr(result.state, name), copy=True, order='K') for name in STATE_ARRAYS}
    jax_record, key_data = key_record(result.master_key)
    data.update(positions=np.stack([p.values for p in result.positions]),
        factor_ids=np.array([p.factor_id for p in result.positions], dtype=str),
        field_steps=np.array([t.step_size for t in tuning], np.float64),
        hyper_steps=np.array([t.hyper_step_size for t in tuning], np.float64),
        inverse_mass=np.stack([t.inverse_mass_matrix for t in tuning]),
        b_sigma2=np.array(b_sigma2, copy=True), master_key=key_data,
        numpy_global_keys=global_state[1].copy())
    # Preserve all spectral arrays and scalar constants, plus the entire audit.
    data.update({'spectral_'+k: np.array(v, copy=True, order='K')
                 for k, v in target.geometry.spectral.items() if k != 'audit'})
    meta = dict(schema=SCHEMA, contract=contract_record, contract_sha256=contract.sha256,
        progress=validate_progress(progress), boundary=boundary,
        position_bindings=[dict(factor_id=p.factor_id, target_identity=p.target_identity) for p in result.positions],
        tuning_bindings=[dict(factor_id=t.factor_id, target_identity=t.target_identity, mass_sha256=t.mass_sha256) for t in tuning],
        rng=dict(eta=generator_record(eta_rng), gauge=generator_record(gauge_rng),
                 numpy_global=global_record(global_state), jax=jax_record),
        spectral_audit=parse_json(json_text(target.geometry.spectral['audit'])),
        arrays={k: _descriptor(v) for k, v in data.items()})
    meta['logical_sha256'] = digest(meta)
    data['metadata'] = np.array(json_text(meta))
    return data


def _validate_payload(data, target, contract):
    if 'metadata' not in data:
        raise ValueError('Missing checkpoint metadata')
    raw = data['metadata']
    if raw.dtype.kind != 'U' or raw.shape != ():
        raise ValueError('Scalar Unicode JSON metadata required; pickle forbidden')
    meta = parse_json(str(raw))
    exact_keys(meta, ('schema','contract','contract_sha256','progress','boundary','position_bindings',
                     'tuning_bindings','rng','spectral_audit','arrays','logical_sha256'))
    expected_keys = set(STATE_ARRAYS) | {'positions','factor_ids','field_steps','hyper_steps',
        'inverse_mass','b_sigma2','master_key','numpy_global_keys'} | {
        'spectral_'+k for k in target.geometry.spectral if k != 'audit'}
    exact_keys(meta['arrays'], expected_keys)
    if set(data) != expected_keys | {'metadata'}:
        raise ValueError('Missing or incompatible checkpoint array fields')
    if meta['schema'] != SCHEMA or digest({k:v for k,v in meta.items() if k != 'logical_sha256'}) != meta['logical_sha256']:
        raise ValueError('Checkpoint schema or metadata hash mismatch')
    for name in expected_keys:
        if json_text(_descriptor(data[name])) != json_text(meta['arrays'][name]):
            raise ValueError('Array dtype/shape/order/hash mismatch: '+name)
    record = validate_contract(contract, target, data['b_sigma2'])
    if json_text(meta['contract']) != contract.json or meta['contract_sha256'] != contract.sha256:
        raise ValueError('Checkpoint software/run/target contract mismatch')
    progress = validate_progress(meta['progress'])
    if json_text(meta['spectral_audit']) != json_text(target.geometry.spectral['audit']):
        raise ValueError('Spectral audit mismatch; target must not be replaced')
    for key, value in target.geometry.spectral.items():
        if key == 'audit':
            continue
        actual, expected = data['spectral_'+key], np.asarray(value)
        if (actual.dtype != expected.dtype or actual.shape != expected.shape
                or not np.array_equal(actual, expected)):
            raise ValueError('Spectral chart mismatch: '+key)
        # Structural log(0)=-inf is valid only in the authenticated log diagonals.
        if np.isnan(actual).any() or np.isposinf(actual).any() or (key != 'log_modal_diagonals' and not np.isfinite(actual).all()):
            raise ValueError('Invalid spectral value')
    k = len(target.factor_ids)
    ids = data['factor_ids']
    if ids.dtype.kind != 'U' or ids.shape != (k,) or tuple(ids.tolist()) != target.factor_ids:
        raise ValueError('Factor identities/order mismatch')
    state = GaussianState(**{n: data[n].copy(order='K') for n in STATE_ARRAYS},
                          input_identity_json=target.inputs.identity_json)
    state.validate(target.inputs, factors=k)
    dimension = target.position_dimension
    array(data['positions'], 'positions', (k, dimension))
    array(data['field_steps'], 'field steps', (k,), positive=True)
    array(data['hyper_steps'], 'hyper steps', (k,), positive=True)
    array(data['inverse_mass'], 'inverse mass', (k, dimension), positive=True)
    if (not isinstance(meta['position_bindings'], list) or len(meta['position_bindings']) != k
            or not isinstance(meta['tuning_bindings'], list) or len(meta['tuning_bindings']) != k):
        raise ValueError('Incomplete position/tuning bindings')
    positions, tuning = [], []
    split = SplitTransition(target)
    # Restore only a functional JAX key here; it never mutates a random stream.
    exact_keys(meta['rng'], ('eta','gauge','numpy_global','jax'))
    key = restore_key(meta['rng']['jax'], data['master_key'])
    for i, fid in enumerate(target.factor_ids):
        pb, tb = meta['position_bindings'][i], meta['tuning_bindings'][i]
        if pb != dict(factor_id=fid, target_identity=target.identity):
            raise ValueError('Position binding mismatch')
        if tb != dict(factor_id=fid, target_identity=target.identity, mass_sha256=logical_hash(data['inverse_mass'][i])):
            raise ValueError('Tuning binding mismatch')
        values, mass = data['positions'][i].copy(), data['inverse_mass'][i].copy()
        values.flags.writeable = mass.flags.writeable = False
        p = FieldPosition(values, fid, target.identity)
        t = SplitTuning(target.identity, fid, float(data['field_steps'][i]),
                        float(data['hyper_steps'][i]), mass, tb['mass_sha256'])
        split.validate_inputs(key, p, state, t, state_factor_ids=target.factor_ids)
        positions.append(p); tuning.append(t)
    # Fresh local RNGs only, after complete array/state/identity validation.
    eta_rng = restore_generator(meta['rng']['eta'])
    gauge_rng = restore_generator(meta['rng']['gauge'])
    global_state = restore_global(meta['rng']['numpy_global'], data['numpy_global_keys'])
    exact_keys(meta['boundary'], ('state_after','positions_after','target_sha256',
                                 'b_sigma2_sha256','rng_after','label','fitted_Y_sha256'))
    label = meta['boundary']['label']
    if not isinstance(label, str) or not label:
        raise ValueError('Completed sweep label required')
    boundary = _boundary(state, positions, target, data['b_sigma2'],
                         stream_audit(eta_rng, gauge_rng, key, global_state), label)
    if json_text(meta['boundary']) != json_text(boundary):
        raise ValueError('Completed boundary state/RNG/fitted value mismatch')
    return RestartState(state, tuple(positions), tuple(tuning), eta_rng, gauge_rng,
        global_state, key, data['b_sigma2'].copy(), progress, contract, boundary, meta['logical_sha256'])


def load_checkpoint(path, *, target, contract):
    """Inspect/reconstruct locally. Caller explicitly installs numpy_global_state."""
    # Own the stream even when NumPy rejects an invalid ZIP before entering its
    # context manager; corrupted-file failures must not leak an open handle.
    with Path(path).open('rb') as stream:
        with np.load(stream, allow_pickle=False) as source:
            if len(source.files) != len(set(source.files)):
                raise ValueError('Duplicate archive members')
            data = {name: source[name].copy(order='K') for name in source.files}
    return _validate_payload(data, target, contract)


def save_checkpoint_atomic(path, *, target, contract, result, tuning, eta_rng,
                           gauge_rng, b_sigma2, progress):
    """Flush, close, validate and atomically replace; retain failed attempts."""
    data = _payload(target, contract, result, tuning, eta_rng, gauge_rng, b_sigma2, progress)
    _validate_payload(data, target, contract)
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.'+path.name+'.attempt-', suffix='.npz', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            np.savez_compressed(stream, **data)
            stream.flush()
            os.fsync(stream.fileno())
        restored = load_checkpoint(temporary, target=target, contract=contract)
        raw = Path(temporary).read_bytes()
        receipt = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                       logical_sha256=restored.logical_sha256, schema=SCHEMA)
        os.replace(temporary, path)
        return receipt
    except Exception as exc:
        raise CheckpointWriteError(temporary) from exc
