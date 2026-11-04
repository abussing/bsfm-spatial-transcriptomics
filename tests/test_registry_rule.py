import hashlib
import json
from pathlib import Path
import unittest
import jax
import numpy as np
from bsfm.sampler.registry_rule import load_registry_rule

ROOT=Path(__file__).resolve().parents[1]
jax.config.update('jax_enable_x64',True)


class RegistryRuleTests(unittest.TestCase):
    def test_registered_orders_and_exact_payloads(self):
        for order,name in [(4,'docs/sampler/s10-subset-smoke-20261103/L4_ell14_smoke.json'),
                           (14,'docs/holdouts/s10-grid-20261103/L14_ell14.json'),
                           (16,'config/sampler/L16_ell14.json')]:
            p=ROOT/name;raw=p.read_bytes();sha=hashlib.sha256(raw).hexdigest()
            rule=load_registry_rule(p,expected_sha256=sha,order=order);rule.validate()
            for k,v in json.loads(raw)['arrays'].items():
                np.testing.assert_array_equal(rule.arrays[k],np.asarray(v,np.float64))
            self.assertEqual(rule.arrays['omega'].shape,(2*order**2,2))
            with self.assertRaises(ValueError):load_registry_rule(p,expected_sha256=sha,order=order+1)
            with self.assertRaises(ValueError):load_registry_rule(p,expected_sha256='0'*64,order=order)


if __name__=='__main__':unittest.main()
