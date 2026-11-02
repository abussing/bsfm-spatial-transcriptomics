"""Validated deterministic warp foundation; no likelihood or sampler transition.

Low-level JAX kernels live in spectral/active. This host boundary authenticates
fixed identities and rejects invalid physical parameters before evaluating them.
"""
from dataclasses import dataclass
import json
from types import MappingProxyType

import jax.numpy as jnp
import jax.scipy.linalg as jsla
import numpy as np
import math
from scipy import sparse

from bsfm.mesh.october26 import dense_mm as _mesh_dense_mm
from bsfm.mesh.projectors import active as projector_support, validate as validate_projector
from .contracts import array, logical_hash
from .spectral import build_spectral_fem_artifact
from .active import active_geometry
from .projector_encoding import barycentric_triplets

# F/generate_splusu_phase1.py:28-35; preserve the original evaluation order.
NU_U = 5.0
ALPHA_FEM = 6
D_FEM = 2.0
NORMCONST = float(math.gamma(int(NU_U)) / math.gamma(ALPHA_FEM)
                  / (4.0 * np.pi) ** (D_FEM / 2.0))
BINOM = np.asarray([1, 6, 15, 20, 15, 6, 1], np.float64)
BINOM.flags.writeable = False
SPECTRAL_TOLERANCE = 2e-10
PROJECTOR_TOLERANCE = 5e-12
PHYSICAL_W_TOLERANCE = 2e-8
KEYS = ('terms', 'vertices', 'projector', 'locations', 'active_indices',
        'vertex_ids', 'cell_ids', 'source_rows')


def dense_mm(path):
    """Reuse canonical Matrix Market reader; historical helper requires float64."""
    return np.asarray(_mesh_dense_mm(path), np.float64)


def validate_mesh(data):
    if set(data) != set(KEYS):
        raise ValueError('Warp input fields missing or unexpected')
    v = array(data['vertices'], 'vertices', ndim=2)
    if v.shape[1] != 2:
        raise ValueError('Two coordinate columns required')
    n = len(v)
    t = array(data['terms'], 'terms', (7, n, n))
    for m in t:
        if np.linalg.norm(m-m.T) > SPECTRAL_TOLERANCE*max(np.linalg.norm(m), np.finfo(float).tiny):
            raise ValueError('Asymmetric FEM term')
    a = array(data['projector'], 'projector', ndim=2)
    xy = array(data['locations'], 'locations', (len(a), 2))
    if a.shape[1] != n:
        raise ValueError('Full projector/FEM dimension mismatch')
    validate_projector(sparse.csr_matrix(a), v, xy, PROJECTOR_TOLERANCE)
    idx = data['active_indices']
    if (not isinstance(idx, np.ndarray) or idx.dtype.kind not in 'iu' or idx.ndim != 1
            or not np.array_equal(idx, projector_support(sparse.csr_matrix(a)))):
        raise ValueError('Active indices must equal sorted full-projector support')
    for key, length in [('vertex_ids', n), ('cell_ids', len(a))]:
        x = data[key]
        if (not isinstance(x, np.ndarray) or x.dtype.kind != 'U' or x.shape != (length,)
                or np.any(x == '') or len(np.unique(x)) != length):
            raise ValueError('Unique ordered Unicode identities required: '+key)
    rows = data['source_rows']
    if (not isinstance(rows, np.ndarray) or rows.dtype.kind not in 'iu'
            or rows.shape != (len(a),) or np.any(rows < 0) or len(np.unique(rows)) != len(a)):
        raise ValueError('Unique nonnegative source rows required')
    # Preserve historical gather threshold and reconstruction check; no new snapping.
    return barycentric_triplets(a[:, idx])


def mesh_identity(data, *, section, mesh_sha256):
    """Declaration to compare against independent bundle identities, not file I/O."""
    validate_mesh(data)
    if (not isinstance(section, str) or not section or not isinstance(mesh_sha256, str)
            or len(mesh_sha256) != 64 or any(c not in '0123456789abcdef' for c in mesh_sha256)):
        raise ValueError('Section and mesh artifact SHA-256 required')
    return dict(schema='bsfm.sampler-warp-input.v1', section=section,
                mesh_sha256=mesh_sha256, coordinate_system='october26_glial_min_max_span',
                axis_order=['center_y', 'center_x'], units='normalized', index_base=0,
                law='full_spectrum_raw_Q', arrays={k: logical_hash(data[k]) for k in KEYS})


def _parameters(log_ell, log_r):
    for x in (log_ell, log_r):
        if isinstance(x, (bool, np.bool_)) or np.ndim(x) != 0 or not np.isfinite(x):
            raise ValueError('Finite scalar log range and log r required')
    # Match selected direct-W coupling in log space; no extra amplitude parameter.
    with np.errstate(over='ignore', under='ignore'):
        ell = float(np.exp(log_ell))
        ratio = float(np.exp(log_r))
        sigma = float(np.exp(log_ell + log_r - np.log(np.sqrt(10.0))))
    if not all(np.isfinite(x) and x > 0 for x in (ell, ratio, sigma)):
        raise ValueError('Range/amplitude overflow or underflow; no clipping')
    return sigma


@dataclass(frozen=True)
class WarpGeometry:
    arrays: object
    identity_json: str
    spectral: object
    spectral_identity: str

    @classmethod
    def authenticate(cls, data, expected):
        copied = {k: np.array(v, copy=True, order='K') for k, v in data.items()}
        try:
            actual = mesh_identity(copied, section=expected['section'], mesh_sha256=expected['mesh_sha256'])
        except (KeyError, TypeError) as exc:
            raise ValueError('Malformed expected warp identity') from exc
        if actual != expected:
            raise ValueError('Warp input identity/order mismatch')
        terms = copied['terms']
        spec = build_spectral_fem_artifact(terms[0], terms[1:], BINOM, NORMCONST,
                                          NU_U, D_FEM, copied['projector'])
        for values in (copied, spec):
            for a in values.values():
                if isinstance(a, np.ndarray):
                    a.flags.writeable = False
        signature = _spectral_identity(spec)
        return cls(MappingProxyType(copied), json.dumps(actual, sort_keys=True),
                   MappingProxyType(spec), signature)

    def validate(self):
        expected = json.loads(self.identity_json)
        if mesh_identity(self.arrays, section=expected['section'], mesh_sha256=expected['mesh_sha256']) != expected:
            raise ValueError('Warp input mutated')
        if _spectral_identity(self.spectral) != self.spectral_identity:
            raise ValueError('Spectral chart mutated')

    def geometry(self, log_ell):
        self.validate()
        _parameters(log_ell, 0.)
        result = active_geometry(log_ell, self.spectral['U'][self.arrays['active_indices']], self.spectral)
        l, lr, cov, covr, geo = result
        for a in (l, lr, cov, covr, *geo.values()):
            if not np.isfinite(np.asarray(a)).all():
                raise ValueError('Nonfinite warp geometry; no jitter/fallback')
        if np.any(np.diag(l) <= 0) or np.any(np.asarray(geo['modal_sd']) <= 0):
            raise ValueError('Nonpositive root or lost full mode')
        return result

    def physical(self, log_ell, log_r, z):
        sigma = _parameters(log_ell, log_r)
        l, lr, cov, covr, geo = self.geometry(log_ell)
        idx = self.arrays['active_indices']
        array(z, 'z', (len(idx), 2))
        # Same selected historical matrix products. No additive identity/displacement.
        wa = sigma * (l @ jnp.asarray(z))
        aa = jnp.asarray(self.arrays['projector'][:, idx])
        cell = aa @ wa
        # Partial root derivative holds amplitude fixed. Coupled derivative adds W.
        partial = sigma * (lr @ jnp.asarray(z))
        result = dict(W_active=wa, W_cell=cell, sigma_W=sigma,
                      W_active_log_ell_fixed_sigma=partial,
                      W_active_log_ell=partial+wa, W_cell_log_ell=aa@(partial+wa),
                      W_active_log_r=wa, W_cell_log_r=cell)
        if not all(np.isfinite(np.asarray(v)).all() for v in result.values()):
            raise ValueError('Nonfinite physical warp')
        return result

    def rewhiten(self, physical_w, log_ell, log_r):
        """Deterministic inverse coordinate map; no hyperparameter transition."""
        sigma = _parameters(log_ell, log_r)
        l = self.geometry(log_ell)[0]
        array(physical_w, 'physical W', (len(l), 2))
        z = np.asarray(jsla.solve_triangular(l, jnp.asarray(physical_w)/sigma, lower=True))
        restored = np.asarray(sigma*(l@z))
        error = float(np.max(np.abs(restored-physical_w)))
        if not np.isfinite(z).all() or not np.isfinite(error) or error > PHYSICAL_W_TOLERANCE:
            raise RuntimeError('Physical W rewhitening invariant failed')
        return z, dict(max_absolute_error=error, tolerance=PHYSICAL_W_TOLERANCE)


def _spectral_identity(spec):
    return json.dumps({k: logical_hash(v) if isinstance(v, np.ndarray) else v
                       for k, v in spec.items()}, sort_keys=True)
