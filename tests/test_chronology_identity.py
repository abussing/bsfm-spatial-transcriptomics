"""Source identity compatibility is limited to the exact observer-only edit."""
import hashlib
from pathlib import Path
import unittest
from bsfm.sampler import layer6
from bsfm.sampler.checkpoint_contract import chronology_source_hash, fixed_requirements

class ChronologyIdentityTests(unittest.TestCase):
    def test_exact_observer_removal_recovers_original_bytes(self):
        source=Path(layer6.__file__).read_bytes()
        self.assertEqual(hashlib.sha256(source).hexdigest(),
                         'c7091fd46679d8681b1a34ecd365719a40bbb77e13e7ac0f04cd0cb5a21f9a9f')
        self.assertEqual(chronology_source_hash(source),
                         '4bca79cfa48e10d7525d00593bb55e3e84aca5741f0bc9ee81588049c6538780')
        self.assertEqual(fixed_requirements()['layer6_source_sha256'],chronology_source_hash(source))

    def test_other_edits_are_not_admitted_as_equivalent(self):
        source=Path(layer6.__file__).read_bytes()
        for changed in (source.replace(b'N_INNER = 3',b'N_INNER = 4'),
                        source.replace(b"observe('after_px')",b"observe('after_px', x=1)"),
                        source+b'\n'):
            self.assertNotEqual(changed,source)
            self.assertEqual(chronology_source_hash(changed),hashlib.sha256(changed).hexdigest())
            self.assertNotEqual(chronology_source_hash(changed),chronology_source_hash(source))
