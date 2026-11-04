"""Synthetic runtime authentication; these are not GPU execution tests."""
import base64
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from bsfm.sampler import run_gpu_environment as gpu


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class GPUEnvironmentTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.prefix = self.root/'environment'
        self.installed = self.prefix/'lib/python3.11/site-packages'
        self.installed.mkdir(parents=True)
        self.exe = self.prefix/'python'; self.exe.write_bytes(b'interpreter')
        self.libdevice = self.root/'libdevice.bc'; self.libdevice.write_bytes(b'cuda')
        self.module = self.installed/'numpy/core.py'
        self.module.parent.mkdir(); self.module.write_bytes(b'constant = 1\n')
        h = base64.urlsafe_b64encode(bytes.fromhex(sha(self.module))).decode().rstrip('=')
        self.record = self.installed/'numpy.dist-info/RECORD'
        self.record.parent.mkdir()
        self.record.write_text(f'numpy/core.py,sha256={h},{self.module.stat().st_size}\n', encoding='utf-8')
        self.distribution = SimpleNamespace(metadata={'Name': 'numpy'}, version='2.1.3',
            locate_file=lambda name: self.installed/name,
            read_text=lambda name: self.record.read_text(encoding='utf-8'))
        self.receipt = self.root/'runtime.json'
        self.receipt.write_text(json.dumps(dict(python='fixture interpreter',
            packages={'numpy':'2.1.3'}, python_sha256=sha(self.exe),
            libdevice_sha256=sha(self.libdevice),
            record_hashes={str(self.record.relative_to(self.installed)):sha(self.record)})), encoding='utf-8')
        self.p100 = self.root/'p100.json'
        self.p100.write_text(json.dumps(dict(status='COMPLETED', exit_code='0:0',
                                           focused_tests_passed=4)), encoding='utf-8')
        self.args = dict(receipt=self.receipt, expected_sha256=sha(self.receipt),
            prefix=self.prefix, site_packages=self.installed, libdevice=self.libdevice,
            p100_receipt=self.p100, p100_sha256=sha(self.p100), blas_threads=1)

    def runtime(self, *, backend='gpu', device='Tesla V100', threads=1):
        stack = ExitStack(); self.addCleanup(stack.close)
        stack.enter_context(patch.object(gpu, 'sys', SimpleNamespace(prefix=str(self.prefix),
            executable=str(self.exe), version='fixture interpreter')))
        stack.enter_context(patch.object(gpu.site, 'ENABLE_USER_SITE', False))
        stack.enter_context(patch.object(gpu.jax, 'default_backend', return_value=backend))
        stack.enter_context(patch.object(gpu.jax, 'config', SimpleNamespace(x64_enabled=True)))
        stack.enter_context(patch.object(gpu.jax, 'devices', return_value=[SimpleNamespace(device_kind=device)]))
        stack.enter_context(patch.dict(gpu.os.environ, {'BSFM_EXPERIMENTAL_CUDA':'1'}))
        stack.enter_context(patch.object(gpu.metadata, 'distributions', return_value=[self.distribution]))
        stack.enter_context(patch.object(gpu, 'threadpool_info', return_value=[{'num_threads':threads}]))
        return stack

    def test_recorded_v100_and_p100(self):
        for device in ('Tesla V100', 'Tesla P100'):
            with self.runtime(device=device):
                result = gpu.authenticate_gpu_environment(**self.args)
                self.assertEqual(result['device_kind'], device)
                self.assertEqual(result['installed_numerical_files'], 1)
                self.assertEqual(result['lock']['sha256'], sha(self.receipt))
                self.assertEqual(result['device_validation']['sha256'],
                                 sha(self.p100 if 'P100' in device else self.receipt))

    def test_cpu_and_unknown_gpu_rejected(self):
        with self.runtime(backend='cpu'):
            with self.assertRaisesRegex(ValueError, 'GPU/x64'):
                gpu.authenticate_gpu_environment(**self.args)
        with self.runtime(device='Unknown accelerator'):
            with self.assertRaisesRegex(ValueError, 'Validated V100 or P100'):
                gpu.authenticate_gpu_environment(**self.args)

    def test_pinned_receipts_and_runtime_files(self):
        with self.runtime():
            for name in ('receipt', 'libdevice'):
                p = self.args[name]; original = p.read_bytes(); p.write_bytes(original+b' ')
                with self.assertRaises(ValueError): gpu.authenticate_gpu_environment(**self.args)
                p.write_bytes(original)
            self.module.write_bytes(b'constant = 2\n')
            with self.assertRaisesRegex(ValueError, 'numerical file changed'):
                gpu.authenticate_gpu_environment(**self.args)
        with self.runtime(device='Tesla P100'):
            self.p100.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'P100 validation receipt changed'):
                gpu.authenticate_gpu_environment(**self.args)

    def test_paths_packages_threads_and_optin(self):
        with self.runtime():
            with self.assertRaisesRegex(ValueError, 'inside'):
                gpu.authenticate_gpu_environment(**dict(self.args, site_packages=self.root))
            with patch.object(gpu.metadata, 'distributions', return_value=[self.distribution]*2):
                with self.assertRaisesRegex(ValueError, 'package versions'):
                    gpu.authenticate_gpu_environment(**self.args)
            with patch.dict(gpu.os.environ, {'BSFM_EXPERIMENTAL_CUDA':'0'}):
                with self.assertRaisesRegex(ValueError, 'GPU/x64'):
                    gpu.authenticate_gpu_environment(**self.args)
        with self.runtime(threads=4):
            with self.assertRaisesRegex(ValueError, 'BLAS thread'):
                gpu.authenticate_gpu_environment(**self.args)

    def test_cpu_callback_preflight_fails_before_jit(self):
        with patch.object(gpu.jax, 'default_backend', return_value='cpu'), \
             patch.object(gpu.jax, 'jit', side_effect=AssertionError('Unexpected JIT')):
            with self.assertRaisesRegex(ValueError, 'GPU computation backend'):
                gpu.preflight_gpu_callback()

    def test_existing_runtime_entry_dispatches_without_cpu_fallback(self):
        from bsfm.sampler.run_inputs import authenticate_environment
        with self.runtime():
            self.assertEqual(authenticate_environment(gpu_runtime=self.args),
                             gpu.authenticate_gpu_environment(**self.args))
        with self.runtime(backend='cpu'):
            with self.assertRaisesRegex(ValueError, 'GPU/x64'):
                authenticate_environment(gpu_runtime=self.args)


if __name__ == '__main__': unittest.main()
