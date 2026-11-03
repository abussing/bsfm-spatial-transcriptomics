"""Explicit noncanonical L4 rule used only by the requested execution smoke."""
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
import jax
import numpy as np
from bsfm.sampler.contracts import array, logical_hash

RULE_SHA256='5ebf7561ee4a72b609ebd4639d584d11360f93dd07ebf5ab4f53db75c2165168'
REGISTRY=Path(__file__).with_name('L4_ell14_smoke.json')


@dataclass(frozen=True)
class SmokeRule:
    arrays: object
    identity_json: str

    def validate(self):
        expected=load_smoke_rule()
        if self.identity_json!=expected.identity_json or set(self.arrays)!=set(expected.arrays):
            raise ValueError('Smoke rule identity changed')
        for k,v in self.arrays.items():
            if logical_hash(v)!=logical_hash(expected.arrays[k]):
                raise ValueError('Smoke rule array changed')


def load_smoke_rule():
    raw=REGISTRY.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=RULE_SHA256:
        raise ValueError('Smoke rule registry changed')
    record=json.loads(raw)
    arrays={k:np.asarray(v,np.float64) for k,v in record['arrays'].items()}
    nodes=2*record['order']**2
    if record['frequency_nodes']!=nodes or record['feature_columns']!=2*nodes:
        raise ValueError('Rule order/dimension declaration mismatch')
    array(arrays['omega'],'smoke omega',(nodes,2))
    array(arrays['weights'],'smoke weights',(nodes,),positive=True)
    array(arrays['sqrt_weights'],'smoke sqrt weights',(nodes,),positive=True)
    np.testing.assert_allclose(arrays['weights'].sum(),1.,atol=2e-14,rtol=0)
    np.testing.assert_allclose(arrays['sqrt_weights']**2,arrays['weights'],rtol=1e-12,atol=0)
    if not jax.config.x64_enabled or {k:logical_hash(v) for k,v in arrays.items()}!=record['logical_hashes']:
        raise ValueError('Smoke rule dtype/hash contract')
    identity={k:record[k] for k in ('schema','order','ell_eta','frequency_nodes','feature_columns','feature_order','x64_required','scientific_use_approved','table_sha256','logical_hashes')}
    identity['registry_sha256']=RULE_SHA256
    for v in arrays.values():v.flags.writeable=False
    return SmokeRule(MappingProxyType(arrays),json.dumps(identity,sort_keys=True))
