"""Layer-1 float64 state and ordered input identities; no preprocessing.

Contracts validate without consuming RNG or changing numerical array layout.
The state below is only the Gaussian/shrinkage state, not a full MCMC checkpoint.
"""
from dataclasses import dataclass
import hashlib
import json
import re
from types import MappingProxyType

import numpy as np

SHARING = 0.20
MU_LOG_ALPHA = float(np.log(0.7))
VAR_LOG_ALPHA = 0.7
A_PHI = B_PHI = 1.5
A_DELTA1 = 2.1
A_DELTA_LATER = 1.5
INPUT_KEYS = ('Y', 'slocs', 'cell_id', 'cell_names', 'source_row_indices',
              'gene_names', 'cell_type_names')


def dimension(value, name):
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < 1:
        raise ValueError(f'{name} must be a positive integer')
    return int(value)


def array(value, name, shape=None, ndim=None, positive=False, nonnegative=False):
    if not isinstance(value, np.ndarray) or value.dtype != np.dtype('float64'):
        raise ValueError(f'{name} must be a float64 ndarray; no implicit conversion')
    if (shape is not None and value.shape != shape) or (ndim is not None and value.ndim != ndim):
        raise ValueError(f'{name} shape mismatch')
    if value.size == 0 or not np.isfinite(value).all():
        raise ValueError(f'{name} must be nonempty and finite')
    if positive and np.any(value <= 0):
        raise ValueError(f'{name} must be positive')
    if nonnegative and np.any(value < 0):
        raise ValueError(f'{name} must be nonnegative')
    return value


def slices(cell_slc, cells, types):
    if not isinstance(cell_slc, (tuple, list)) or len(cell_slc) != types:
        raise ValueError('one explicit contiguous slice per type required')
    start = 0
    for sl in cell_slc:
        if not isinstance(sl, slice) or sl.step not in (None, 1):
            raise ValueError('unit-step slices required')
        if (not isinstance(sl.start, (int, np.integer)) or isinstance(sl.start, (bool, np.bool_))
                or not isinstance(sl.stop, (int, np.integer)) or isinstance(sl.stop, (bool, np.bool_))
                or sl.start != start or not start < sl.stop <= cells):
            raise ValueError('type slices must partition every cell once in order')
        start = sl.stop
    if start != cells:
        raise ValueError('type slices do not cover all cells')


def loading_shape(loading):
    array(loading, 'Lambda', ndim=3)
    return loading.shape


def sharing(s, factors):
    array(s, 's', (factors,))
    if not np.all(s == SHARING):
        raise ValueError('selected architecture fixes s=0.20')


def fitted_inputs(loading, eta, cell_slc):
    c, g, k = loading_shape(loading)
    array(eta, 'eta', ndim=2)
    if eta.shape[0] != k:
        raise ValueError('eta factor dimension mismatch')
    slices(cell_slc, eta.shape[1], c)


def quadratic_inputs(loading, s, cn):
    c, _, k = loading_shape(loading)
    if dimension(cn, 'Cn') != c:
        raise ValueError('Cn does not match Lambda')
    sharing(s, k)


def lambda_inputs(y, eta, sigma2, v, alpha, phi, tau, s, cell_slc):
    array(y, 'Y', ndim=2); array(eta, 'eta', ndim=2)
    g, n = y.shape; k = eta.shape[0]
    if eta.shape[1] != n:
        raise ValueError('eta cell dimension mismatch')
    if not isinstance(cell_slc, (tuple, list)) or not cell_slc:
        raise ValueError('type slices required')
    slices(cell_slc, n, len(cell_slc))
    array(sigma2, 'sigma2', (g,), positive=True)
    array(alpha, 'alpha', (k,), positive=True)
    array(phi, 'phi', (g, k), positive=True)
    array(tau, 'tau', (k,), positive=True)
    sharing(s, k); unit_weights(v, y.shape)


def unit_weights(v, shape):
    array(v, 'v', shape)
    if not np.all(v == 1):
        raise ValueError('selected Gaussian path requires v=1')


def noise_inputs(y, yhat, v, a, b):
    array(y, 'Y', ndim=2); array(yhat, 'Yhat', y.shape)
    unit_weights(v, y.shape)
    if a != 2.0:
        raise ValueError('selected noise prior shape is 2')
    array(b, 'b_sigma', (y.shape[0],), positive=True)
    if not np.array_equal(b, .25 * np.var(y, axis=1)):
        raise ValueError('b_sigma must be the fixed .25*population_variance(Y)')


def shrinkage_inputs(q, alpha, cn, g, k):
    dimension(cn, 'Cn'); dimension(g, 'G'); dimension(k, 'K')
    array(q, 'qgk', (g, k), nonnegative=True)
    array(alpha, 'alpha', (k,), positive=True)


def phi_inputs(q, alpha, tau, cn, g, k, a, b):
    shrinkage_inputs(q, alpha, cn, g, k)
    array(tau, 'tau', (k,), positive=True)
    if (a, b) != (A_PHI, B_PHI):
        raise ValueError('selected phi prior is Gamma(1.5,1.5)')


def delta_inputs(q, alpha, phi, delta, k, cn, g, a1, alater):
    shrinkage_inputs(q, alpha, cn, g, k)
    array(phi, 'phi', (g, k), positive=True)
    array(delta, 'delta', (k,), positive=True)
    if (a1, alater) != (A_DELTA1, A_DELTA_LATER):
        raise ValueError('selected delta shapes are 2.1 and 1.5')


def px_inputs(loading, eta, alpha, rng, s, label):
    c, g, k = loading_shape(loading)
    array(eta, 'eta', ndim=2)
    if eta.shape[0] != k:
        raise ValueError('eta factor dimension mismatch')
    array(alpha, 'alpha', (k,), positive=True); sharing(s, k)
    if not isinstance(rng, np.random.Generator) or not isinstance(label, str):
        raise ValueError('PX requires an explicit NumPy Generator and string label')


def logical_hash(a):
    """Ordered shape/dtype/value encoding compatible with the GPINIT identity hash."""
    a = np.asarray(a)
    if a.dtype.hasobject:
        raise ValueError('object arrays are forbidden')
    if a.dtype.kind == 'U':
        value = json.dumps(a.tolist(), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        dtype = 'utf8'
    else:
        dtype = a.dtype.newbyteorder('<').str
        value = np.asarray(a, dtype=dtype).tobytes(order='C')
    header = json.dumps({'shape': list(a.shape), 'dtype': dtype}, sort_keys=True).encode()+b'\n'
    return hashlib.sha256(header+value).hexdigest()


def validate_input(data):
    if set(data) != set(INPUT_KEYS):
        raise ValueError('input fields missing or unexpected')
    y = array(data['Y'], 'Y', ndim=2); g, n = y.shape
    array(data['slocs'], 'slocs', (n, 2))
    for key, length in [('cell_names', n), ('gene_names', g), ('cell_type_names', None)]:
        a = data[key]
        if (not isinstance(a, np.ndarray) or a.dtype.kind != 'U' or a.ndim != 1
                or not len(a) or (length is not None and len(a) != length)
                or len(set(a.tolist())) != len(a) or np.any(a == '')):
            raise ValueError(f'{key} must contain unique nonempty ordered Unicode IDs')
    for key in ['cell_id', 'source_row_indices']:
        a = data[key]
        if (not isinstance(a, np.ndarray) or a.dtype.kind not in 'iu'
                or a.shape != (n,) or np.any(a < 0)):
            raise ValueError(f'invalid {key}')
    rows = data['source_row_indices']; codes = data['cell_id']
    if len(np.unique(rows)) != n:
        raise ValueError('duplicate source rows')
    c = len(data['cell_type_names'])
    if np.any(codes >= c) or np.any(codes[:-1] > codes[1:]):
        raise ValueError('cell codes must be contiguous ordered type blocks')
    counts = np.bincount(codes.astype(np.int64), minlength=c)
    if np.any(counts == 0):
        raise ValueError('empty modeled type')
    stops = np.cumsum(counts); starts = np.r_[0, stops[:-1]]
    for a, b in zip(starts, stops):
        if np.any(rows[a:b][1:] <= rows[a:b][:-1]):
            raise ValueError('source rows must increase within type')
    return tuple(slice(int(a), int(b)) for a, b in zip(starts, stops))


def input_identity(data, *, section, response_sha256, coordinate_system):
    """Record a declaration; callers must compare with independently expected identity.

    This does not authenticate an external file or discover physical units.
    coordinate_system identifies the explicit mesh transform; no transform runs here.
    """
    validate_input(data)
    if (not isinstance(section, str) or not section
            or coordinate_system not in ('source_native', 'october26_glial_min_max_span')
            or not isinstance(response_sha256, str)
            or not re.fullmatch('[a-f0-9]{64}', response_sha256)):
        raise ValueError('section, coordinate system and response artifact SHA-256 required')
    return dict(schema='bsfm.sampler-input.v1', section=section,
                response='final_centered_Y', response_sha256=response_sha256,
                coordinate_system=coordinate_system, axis_order=['center_y', 'center_x'],
                units='source_native' if coordinate_system == 'source_native' else 'normalized',
                arrays={k: logical_hash(data[k]) for k in INPUT_KEYS})


@dataclass(frozen=True)
class ModelInput:
    arrays: object
    identity_json: str

    @classmethod
    def authenticate(cls, data, expected):
        # Copy before hashing so caller mutation cannot change the authenticated input.
        copied = {k: np.array(v, copy=True, order='K') for k, v in data.items()}
        try:
            actual = input_identity(copied, section=expected['section'],
                                    response_sha256=expected['response_sha256'],
                                    coordinate_system=expected['coordinate_system'])
        except (KeyError, TypeError) as exc:
            raise ValueError('malformed expected input identity') from exc
        if actual != expected:
            raise ValueError('input identity/order mismatch')
        for a in copied.values():
            a.flags.writeable = False
        return cls(MappingProxyType(copied), json.dumps(actual, sort_keys=True))

    def validate(self):
        expected = json.loads(self.identity_json)
        actual = input_identity(self.arrays, section=expected['section'],
                                response_sha256=expected['response_sha256'],
                                coordinate_system=expected['coordinate_system'])
        if actual != expected:
            raise ValueError('authenticated input mutated')
        return validate_input(self.arrays)


@dataclass
class GaussianState:
    """Only the implemented layer. No W/zW/NUTS/RNG/checkpoint state is implied."""
    loading: np.ndarray
    eta: np.ndarray
    alpha: np.ndarray
    zeta: np.ndarray
    sigma2: np.ndarray
    phi: np.ndarray
    delta: np.ndarray
    tau: np.ndarray
    input_identity_json: str

    def validate(self, inputs, *, factors):
        k = dimension(factors, 'factors'); cell_slc = inputs.validate()
        if self.input_identity_json != inputs.identity_json:
            raise ValueError('state belongs to another input identity')
        g, n = inputs.arrays['Y'].shape; c = len(cell_slc)
        array(self.loading, 'Lambda', (c, g, k)); array(self.eta, 'eta', (k, n))
        array(self.alpha, 'alpha', (k,), positive=True)
        array(self.zeta, 'zeta', (k,), positive=True)
        if np.any(self.zeta >= 1):
            raise ValueError('zeta must be strictly below one')
        array(self.sigma2, 'sigma2', (g,), positive=True)
        array(self.phi, 'phi', (g, k), positive=True)
        array(self.delta, 'delta', (k,), positive=True)
        array(self.tau, 'tau', (k,), positive=True)
        if not np.array_equal(self.tau, np.cumprod(self.delta)):
            raise ValueError('tau must equal cumprod(delta)')
        return cell_slc
