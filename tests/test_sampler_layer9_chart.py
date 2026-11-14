"""Focused review of saved-chart validation; not yet a runtime API acceptance."""
import copy,json,os,sys,unittest
from pathlib import Path
from unittest.mock import patch
REPO=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(REPO/'src'),str(REPO/'tests')]
import numpy as np
from sampler_layer3_support import system
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.run_chart import restore_geometry

class SavedChartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.geometry=system()[0].geometry
    def test_restore_without_eigensolve_and_exact_geometry(self):
        g=self.geometry
        with patch('scipy.linalg.eigh',side_effect=AssertionError('Eigensystem recomputed')):
            restored=restore_geometry(g.arrays,json.loads(g.identity_json),g.spectral,g.spectral_identity)
        self.assertEqual(restored.spectral_identity,g.spectral_identity)
        for k,v in g.spectral.items():
            if isinstance(v,np.ndarray):np.testing.assert_array_equal(v,restored.spectral[k])
        for a,b in zip(g.geometry(-.3)[:4],restored.geometry(-.3)[:4]):np.testing.assert_array_equal(a,b)
    def test_self_consistent_hash_cannot_hide_invalid_basis(self):
        g=self.geometry;s=copy.deepcopy(dict(g.spectral));s['U'][0,0]+=.2
        identity=json.dumps({k:logical_hash(v) if isinstance(v,np.ndarray) else v for k,v in s.items()},sort_keys=True)
        with self.assertRaisesRegex(ValueError,'orthogonality'):
            restore_geometry(g.arrays,json.loads(g.identity_json),s,identity)
    def test_changed_input_identity_rejected(self):
        g=self.geometry;a=dict(g.arrays);a['terms']=a['terms'].copy();a['terms'][0,0,0]+=.1
        with self.assertRaises(ValueError):restore_geometry(a,json.loads(g.identity_json),g.spectral,g.spectral_identity)
    def test_changed_chart_identity_rejected(self):
        g=self.geometry
        with self.assertRaises(ValueError):restore_geometry(g.arrays,json.loads(g.identity_json),g.spectral,'wrong')

    def test_explicit_migration_bounds_log_roundoff_without_replacing_chart(self):
        g=self.geometry;original=np.log;size=int(np.count_nonzero(g.spectral['modal_diagonals']))
        def shifted(amount):
            def log(value):
                result=original(value)
                return result+amount if np.asarray(value).shape==(size,) else result
            return log
        with patch('bsfm.sampler.run_chart.np.log',side_effect=shifted(1e-12)):
            with self.assertRaisesRegex(ValueError,'Saved modal logarithms'):
                restore_geometry(g.arrays,json.loads(g.identity_json),g.spectral,g.spectral_identity)
            audit=[];r=restore_geometry(g.arrays,json.loads(g.identity_json),g.spectral,g.spectral_identity,migration_audit=audit)
            self.assertEqual(r.spectral_identity,g.spectral_identity)
            np.testing.assert_array_equal(r.spectral['log_modal_diagonals'],g.spectral['log_modal_diagonals'])
            self.assertGreater(audit[0]['max_absolute_error'],0)
        with patch('bsfm.sampler.run_chart.np.log',side_effect=shifted(1e-6)):
            with self.assertRaises(ValueError):
                restore_geometry(g.arrays,json.loads(g.identity_json),g.spectral,g.spectral_identity,migration_audit=[])

    def test_roundoff_negative_saved_mode_is_not_silently_accepted(self):
        g=self.geometry;s=copy.deepcopy(dict(g.spectral))
        d=s['modal_diagonals'];index=np.unravel_index(np.argmin(d),d.shape)
        self.assertEqual(d[index],0.)
        d[index]=-1e-15
        identity=json.dumps({k:logical_hash(v) if isinstance(v,np.ndarray) else v for k,v in s.items()},sort_keys=True)
        with self.assertRaisesRegex(ValueError,'nonnegative modal'):
            restore_geometry(g.arrays,json.loads(g.identity_json),s,identity)

if __name__=='__main__':
    result=unittest.TextTestRunner(stream=sys.stdout,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(SavedChartTests))
    sys.exit(not result.wasSuccessful())
