"""Authenticated ordered L16 rule, fixed ell_eta=.14; no rule generation."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import jax
import numpy as np
from .contracts import array, logical_hash

ARTIFACT_SHA256 = 'd2add950144186c9e7f46c36df5db75ae13538e5cd65be9b7951781c04a464e5'
REGISTRY = Path(__file__).resolve().parents[3]/'config/sampler/L16_ell14.json'


def validate_arrays(data):
    if set(data) != {'omega','weights','sqrt_weights'}:
        raise ValueError('Rule array fields')
    array(data['omega'],'omega',(512,2))
    array(data['weights'],'weights',(512,),positive=True)
    array(data['sqrt_weights'],'sqrt_weights',(512,),positive=True)
    # Selected historical rule_contract.py:9-10, unchanged tolerances.
    np.testing.assert_allclose(np.sum(data['weights']),1.,atol=2e-14,rtol=0)
    np.testing.assert_allclose(data['sqrt_weights']**2,data['weights'],rtol=1e-12,atol=0)
    if not jax.config.x64_enabled:
        raise ValueError('L16 target requires JAX x64')


@dataclass(frozen=True)
class FrozenRule:
    arrays: object
    identity_json: str

    @classmethod
    def authenticate(cls, data, expected):
        copied={k:np.array(v,copy=True) for k,v in data.items()}
        validate_arrays(copied)
        actual=dict(schema='bsfm.frozen-L16-rule.v1',order=16,ell_eta=.14,
                    frequency_nodes=512,feature_columns=1024,
                    feature_order='all_cosine_then_all_sine_in_frequency_row_order',
                    x64_required=True,artifact_sha256=ARTIFACT_SHA256,
                    logical_hashes={k:logical_hash(v) for k,v in copied.items()})
        if actual!=expected:
            raise ValueError('Frozen L16 identity/order mismatch')
        for v in copied.values():v.flags.writeable=False
        return cls(MappingProxyType(copied),json.dumps(actual,sort_keys=True))

    def validate(self):
        # Recheck the complete schema/chart as well as bytes. A forged dataclass
        # identity must not relabel the fixed .14 rule while retaining its arrays.
        type(self).authenticate(self.arrays,json.loads(self.identity_json))


def load_rule():
    """Load the canonical registry; full file identity is pinned in the code below."""
    raw=REGISTRY.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=REGISTRY_SHA256:
        raise ValueError('Canonical rule registry bytes changed')
    record=json.loads(raw)
    fields=('schema','order','ell_eta','frequency_nodes','feature_columns',
            'feature_order','x64_required','artifact_sha256','logical_hashes')
    return FrozenRule.authenticate({k:np.asarray(v,np.float64) for k,v in record['arrays'].items()},
                                   {k:record[k] for k in fields})


# Filled from authenticated SOURCE_MANIFEST.json -> original NPZ -> JSON roundtrip.
REGISTRY_SHA256 = 'e39e1597b842b1c71698e9ee180cff3632b6f7b966f9cdaadef1ee13214812d9'
