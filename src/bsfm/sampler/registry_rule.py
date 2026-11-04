"""Load an explicitly chosen, hash-pinned finite-feature quadrature registry.

Order is configuration, not a tensor dimension constant. This does not generate
new quadrature tables or change the canonical L16 checkpoint identity. Existing
experiment adapters remain unchanged for exact continuation of running chains.
"""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import jax
import numpy as np
from .contracts import logical_hash


def _validate(arrays, metadata, order):
    if type(order) is not int or order < 1 or metadata['order'] != order:
        raise ValueError('Explicit positive quadrature order mismatch')
    if not jax.config.x64_enabled or metadata['x64_required'] is not True:
        raise ValueError('Finite-feature rule requires x64')
    # The current model fixes this field scale; making it variable also requires
    # changing the target's scale-reference/prior contract, not just this loader.
    if metadata['ell_eta'] != .14:
        raise ValueError('Current target requires ell_eta=.14')
    n=2*order*order
    if metadata['frequency_nodes']!=n or metadata['feature_columns']!=2*n:
        raise ValueError('Quadrature dimensions disagree with order')
    if metadata['feature_order']!='all_cosine_then_all_sine_in_frequency_row_order':
        raise ValueError('Feature ordering mismatch')
    if set(arrays)!={'omega','weights','sqrt_weights'}:
        raise ValueError('Unexpected quadrature arrays')
    for k,shape in [('omega',(n,2)),('weights',(n,)),('sqrt_weights',(n,))]:
        v=arrays[k]
        if v.dtype!=np.float64 or v.shape!=shape or not np.isfinite(v).all():
            raise ValueError('Invalid quadrature array '+k)
    if np.any(arrays['weights']<=0) or np.any(arrays['sqrt_weights']<=0):
        raise ValueError('Positive quadrature weights required')
    np.testing.assert_allclose(arrays['weights'].sum(),1,atol=2e-14,rtol=0)
    np.testing.assert_allclose(arrays['sqrt_weights']**2,arrays['weights'],rtol=1e-12,atol=0)
    if {k:logical_hash(v) for k,v in arrays.items()}!=metadata['logical_hashes']:
        raise ValueError('Quadrature payload identity mismatch')


@dataclass(frozen=True)
class RegistryRule:
    arrays: object
    identity_json: str
    expected_identity_json: str

    def validate(self):
        if self.identity_json!=self.expected_identity_json:
            raise ValueError('Registry identity changed')
        m=json.loads(self.identity_json)
        _validate(self.arrays,m,m['order'])


def load_registry_rule(path, *, expected_sha256, order):
    """Load exact registered arrays with an explicit expected order and file hash."""
    raw=Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:
        raise ValueError('Quadrature registry hash mismatch')
    metadata=json.loads(raw)
    arrays={k:np.asarray(v,np.float64) for k,v in metadata.pop('arrays').items()}
    _validate(arrays,metadata,order)
    for a in arrays.values():a.flags.writeable=False
    metadata['registry_sha256']=expected_sha256
    identity=json.dumps(metadata,sort_keys=True)
    return RegistryRule(MappingProxyType(arrays),identity,identity)
