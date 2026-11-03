"""Lossless RNG records; decoding never changes process-global or caller RNGs."""
import json
import hashlib
import numpy as np
import jax
import jax.numpy as jnp


def json_text(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def parse_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key')
            result[key] = value
        return result
    def invalid(value):
        raise ValueError('Nonfinite JSON number: '+value)
    return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)


def exact_keys(value, names):
    if not isinstance(value, dict) or set(value) != set(names):
        raise ValueError('Missing or incompatible metadata fields')


def encode(value):
    if isinstance(value, np.ndarray):
        if value.dtype not in (np.dtype('uint32'), np.dtype('uint64')):
            raise ValueError('Unexpected RNG array dtype')
        return dict(rng_array=True, dtype=value.dtype.str, shape=list(value.shape), values=value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    return value


def _decode(value):
    if isinstance(value, dict):
        if 'rng_array' in value:
            exact_keys(value, ('rng_array', 'dtype', 'shape', 'values'))
            if value['rng_array'] is not True or value['dtype'] not in ('<u4', '<u8'):
                raise ValueError('Invalid RNG array encoding')
            result = np.asarray(value['values'], dtype=value['dtype'])
            if list(result.shape) != value['shape'] or encode(result) != value:
                raise ValueError('Lossy RNG state encoding')
            return result
        return {k: _decode(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_decode(v) for v in value]
    return value


BIT_GENERATORS = {name: getattr(np.random, name)
                  for name in ('PCG64', 'PCG64DXSM', 'MT19937', 'Philox', 'SFC64')}


def generator_record(rng):
    if not isinstance(rng, np.random.Generator):
        raise ValueError('Explicit NumPy Generator required')
    name = type(rng.bit_generator).__name__
    if name not in BIT_GENERATORS or type(rng.bit_generator) is not BIT_GENERATORS[name]:
        raise ValueError('Unsupported bit-generator type')
    return dict(type=name, state=encode(rng.bit_generator.state))


def restore_generator(record):
    exact_keys(record, ('type', 'state'))
    if record['type'] not in BIT_GENERATORS:
        raise ValueError('Unsupported bit-generator type')
    # Seed zero avoids entropy acquisition and never uses np.random's global RNG.
    bitgen = BIT_GENERATORS[record['type']](0)
    try:
        bitgen.state = _decode(record['state'])
    except (TypeError, KeyError, OverflowError) as exc:
        raise ValueError('Invalid bit-generator state') from exc
    rng = np.random.Generator(bitgen)
    if json_text(generator_record(rng)) != json_text(record):
        raise ValueError('RNG state changed during restoration')
    return rng


def global_record(state):
    if not isinstance(state, tuple) or len(state) != 5:
        raise ValueError('Complete NumPy global state required')
    name, keys, pos, cached, value = state
    if (name != 'MT19937' or not isinstance(keys, np.ndarray)
            or keys.dtype != np.dtype('uint32') or keys.shape != (624,)
            or type(pos) is not int or not 0 <= pos <= 624
            or type(cached) is not int or cached not in (0, 1)
            or not isinstance(value, float) or not np.isfinite(value)):
        raise ValueError('Invalid NumPy global RNG state')
    return dict(type=name, position=pos, has_gauss=cached, cached_gaussian=value)


def restore_global(record, keys):
    exact_keys(record, ('type', 'position', 'has_gauss', 'cached_gaussian'))
    state = (record['type'], keys.copy(), record['position'], record['has_gauss'], record['cached_gaussian'])
    global_record(state)
    probe = np.random.RandomState(0)
    probe.set_state(state)
    actual = probe.get_state()
    if global_record(actual) != record or not np.array_equal(actual[1], keys):
        raise ValueError('Global state changed during validation')
    return state


def key_record(key):
    try:
        data = np.asarray(jax.random.key_data(key))
        impl = str(jax.random.key_impl(key))
    except (TypeError, ValueError) as exc:
        raise ValueError('Invalid JAX key') from exc
    if impl != 'threefry2x32' or data.dtype != np.dtype('uint32') or data.shape != (2,):
        raise ValueError('Scalar threefry2x32 key required')
    return dict(implementation=impl, representation='legacy' if key.dtype == np.dtype('uint32') else 'typed'), data.copy()


def restore_key(record, data):
    exact_keys(record, ('implementation', 'representation'))
    if (record['implementation'] != 'threefry2x32' or record['representation'] not in ('legacy', 'typed')
            or data.dtype != np.dtype('uint32') or data.shape != (2,)):
        raise ValueError('Invalid JAX key record')
    return (jnp.asarray(data) if record['representation'] == 'legacy'
            else jax.random.wrap_key_data(jnp.asarray(data), impl='threefry2x32'))


def stream_audit(eta_rng, gauge_rng, key, global_state):
    """Layer-6 fingerprint encoding, evaluated on an explicit global snapshot."""
    def convert(x):
        if isinstance(x, np.ndarray):
            return dict(dtype=x.dtype.str, shape=list(x.shape), values=x.tolist())
        if isinstance(x, np.generic):
            return x.item()
        raise TypeError(type(x).__name__)
    def sha(x):
        return hashlib.sha256(json.dumps(x, default=convert, sort_keys=True,
            allow_nan=False, separators=(',', ':')).encode()).hexdigest()
    record, data = key_record(key)
    return dict(numpy_global_sha256=sha(global_state),
        eta_generator=type(eta_rng.bit_generator).__name__, eta_rng_sha256=sha(eta_rng.bit_generator.state),
        gauge_generator=type(gauge_rng.bit_generator).__name__, gauge_rng_sha256=sha(gauge_rng.bit_generator.state),
        jax_impl=record['implementation'], jax_key_data=data.tolist())
