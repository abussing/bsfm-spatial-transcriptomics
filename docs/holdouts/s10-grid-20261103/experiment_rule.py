"""User-selected L14 experiment rule; canonical L16 registry is unchanged."""
from dataclasses import dataclass
from types import MappingProxyType
from pathlib import Path
import hashlib
import json
import jax
import numpy as np
from bsfm.sampler.contracts import logical_hash

SHA='bb74643b60140962a919bca252465149f450fd89f376bab66db653b23c30a5bf'
PATH=Path(__file__).with_name('L14_ell14.json')

@dataclass(frozen=True)
class ExperimentRule:
    arrays: object
    identity_json: str
    def validate(self):
        reference=load_rule()
        if self.identity_json!=reference.identity_json or {k:logical_hash(v) for k,v in self.arrays.items()}!={k:logical_hash(v) for k,v in reference.arrays.items()}:
            raise ValueError('Experiment rule identity changed')

def load_rule():
    raw=PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=SHA:raise ValueError('Changed L14 registry')
    r=json.loads(raw); arrays={k:np.asarray(v,np.float64) for k,v in r.pop('arrays').items()}
    if not jax.config.x64_enabled or arrays['omega'].shape!=(392,2) or arrays['weights'].shape!=(392,):
        raise ValueError('L14 dimensions/x64')
    if {k:logical_hash(v) for k,v in arrays.items()}!=r['logical_hashes']:raise ValueError('L14 payload hashes')
    np.testing.assert_allclose(arrays['weights'].sum(),1.,rtol=0,atol=2e-14)
    np.testing.assert_allclose(arrays['sqrt_weights']**2,arrays['weights'],rtol=1e-12,atol=0)
    if np.any(arrays['weights']<=0):raise ValueError('Nonpositive rule weights')
    for a in arrays.values():a.flags.writeable=False
    r['registry_sha256']=SHA
    return ExperimentRule(MappingProxyType(arrays),json.dumps(r,sort_keys=True))
