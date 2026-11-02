"""Existing tiny R/fmesher environment checks, independent of retired studies."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from bsfm.mesh.identities import REPO


@unittest.skipUnless(os.environ.get('BSFM_MESH_INTEGRATION') == '1',
                     'Set BSFM_MESH_INTEGRATION=1 for R/fmesher integration')
class MeshEnvironmentIntegration(unittest.TestCase):
    def test_fresh_R_mesh_projector_and_cross_language_roundtrip(self):
        spec = json.loads((REPO/'environment/mesh/environment-spec.json').read_text(encoding='utf-8'))
        runtime = json.loads((REPO/'environment/mesh/runtime-lock.json').read_text(encoding='utf-8'))
        environment = Path(spec['external_root'])
        rscript = Path(runtime['R']['path'])
        self.assertTrue(environment.is_dir(), 'Accepted mesh environment required')
        self.assertTrue(rscript.is_file(), 'Accepted immutable R runtime required')
        loader = importlib.util.spec_from_file_location('mesh_environment_checks', REPO/'environment/mesh/validate.py')
        checks = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(checks)
        env = dict(os.environ, LANG='C', LC_ALL='C', OMP_NUM_THREADS='1',
                   OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
        with tempfile.TemporaryDirectory(prefix='bsfm-mesh-environment-test-') as tmp:
            records = []
            for i in (1, 2):
                dest = Path(tmp)/f'fresh-{i}'
                result = subprocess.run([str(rscript), '--vanilla',
                    str(REPO/'environment/mesh/validate.R'), str(environment), str(dest)],
                    env=env, capture_output=True, text=True, timeout=180)
                self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
                self.assertNotIn('stack imbalance', (result.stdout+result.stderr).lower())
                # This is the accepted 13-vertex environment fixture, not a
                # construction policy or a repeat of any real section experiment.
                record = checks.read_run(dest)
                self.assertEqual((record['vertices'], record['triangles']), (13, 16))
                self.assertEqual(record['rejected_index_corruptions'], 2)
                records.append(record)
            self.assertEqual(records[0], records[1])
            result = subprocess.run([str(rscript), '--vanilla',
                str(REPO/'environment/mesh/roundtrip.R'), str(environment), tmp],
                env=env, capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stdout+result.stderr)
            self.assertIn('PYTHON_TO_R_SPARSE_ROUNDTRIP_EXACT', result.stdout)
