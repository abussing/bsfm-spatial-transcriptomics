"""Receipt joins and runtime rejection tests; actual GPU execution is separate."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import unittest

import test_gpu_environment as legacy
from bsfm.sampler import runtime_installation as installation
from bsfm.sampler import run_validated_gpu_environment as validated
from bsfm.sampler.run_inputs import authenticate_environment
from bsfm.sampler.run_storage import file_record


class ValidatedRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.fixture = legacy.GPUEnvironmentTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f = self.fixture
        self.lock = f.root/'environment/sampler-gpu/requirements.lock'
        self.lock.parent.mkdir(parents=True, exist_ok=True)
        self.lock.write_text('pinned synthetic wheels')
        f.distribution.files = [Path('numpy.dist-info/RECORD')]
        receipt = dict(schema='bsfm.candidate-gpu-install.v1', prefix=str(f.prefix),
            python='fixture interpreter', python_sha256=legacy.sha(f.exe),
            packages={'numpy':'2.1.3'}, lock_sha256=legacy.sha(self.lock),
            record_hashes={str(f.record.relative_to(f.prefix)):legacy.sha(f.record)})
        f.receipt.write_text(json.dumps(receipt))
        self.validation = f.root/'validation.json'
        self.result = dict(schema='bsfm.candidate-gpu-validation.v1', status='PASS',
            source_commit='a'*40, installation_sha256=legacy.sha(f.receipt),
            tests_run=12, expected_tests=12, failures=[], errors=[], skipped=[],
            device_kind='NVIDIA A100-SXM4-40GB', payload_files_checked=1,
            callback=dict(backend='gpu', callback_passed=True),
            deep_dense_oracle=dict(value_error=1e-14, gradient_max_error=1e-16))
        self.validation.write_text(json.dumps(self.result))
        self.plan = f.root/'plan.json'
        self.plan_data = dict(schema='bsfm.external-runtime-validation-plan.v1', source_commit='a'*40,
            artifact_records={k:dict(path=str(p),**file_record(p)) for k,p in
                dict(installation=f.receipt, wheel_lock=self.lock, libdevice=f.libdevice).items()})
        self.plan.write_text(json.dumps(self.plan_data))
        self.args = dict(schema=validated.SCHEMA, installation=f.receipt,
            installation_sha256=legacy.sha(f.receipt), validation=self.validation,
            validation_sha256=legacy.sha(self.validation), validation_plan=self.plan,
            validation_plan_sha256=legacy.sha(self.plan), libdevice=f.libdevice, blas_threads=1)

    def runtime(self, **kwargs):
        f = self.fixture
        stack = f.runtime(device=kwargs.get('device','NVIDIA A100-SXM4-40GB'),
                          backend=kwargs.get('backend','gpu'))
        stack.enter_context(patch.object(installation, 'sys', SimpleNamespace(prefix=str(f.prefix),
            executable=str(f.exe), version='fixture interpreter')))
        stack.enter_context(patch.object(validated, 'ROOT', f.root))
        stack.enter_context(patch.object(validated, 'threadpool_info', return_value=[{'num_threads':1}]))
        return stack

    def test_dispatch_and_stable_identity(self):
        with self.runtime():
            a = authenticate_environment(gpu_runtime=self.args)
            self.assertEqual(a, authenticate_environment(gpu_runtime=self.args))
            self.assertEqual(a['schema'], validated.SCHEMA)
            self.assertEqual(a['installed_numerical_files'], 1)
            self.assertEqual(a['validation'], file_record(self.validation))

    def test_incomplete_or_mismatched_evidence_rejected(self):
        for change in [dict(status='FAIL'), dict(tests_run=11), dict(expected_tests=13),
                       dict(skipped=['one']), dict(source_commit='b'*40),
                       dict(installation_sha256='0'*64), dict(device_kind='Tesla V100'),
                       dict(payload_files_checked=2), dict(callback={'backend':'gpu','callback_passed':False}),
                       dict(deep_dense_oracle={'value_error':float('nan'),'gradient_max_error':0})]:
            with self.subTest(change=change), self.runtime():
                self.validation.write_text(json.dumps(dict(self.result, **change)))
                args = dict(self.args, validation_sha256=legacy.sha(self.validation))
                with self.assertRaises(ValueError): authenticate_environment(gpu_runtime=args)

    def test_changed_pins_packages_and_artifacts_rejected(self):
        for path in [self.validation, self.plan, self.fixture.receipt, self.fixture.exe,
                     self.fixture.module, self.fixture.record, self.fixture.libdevice, self.lock]:
            original = path.read_bytes()
            with self.subTest(path=path), self.runtime():
                path.write_bytes(original+b'changed')
                with self.assertRaises(ValueError): authenticate_environment(gpu_runtime=self.args)
            path.write_bytes(original)
        with self.runtime(), patch.object(installation.metadata, 'distributions',
                return_value=[self.fixture.distribution]*2):
            with self.assertRaisesRegex(ValueError, 'closure'):
                authenticate_environment(gpu_runtime=self.args)

    def test_backend_schema_and_threads_rejected(self):
        for kwargs in [dict(backend='cpu'), dict(device='NVIDIA H200')]:
            with self.runtime(**kwargs), self.assertRaises(ValueError):
                authenticate_environment(gpu_runtime=self.args)
        with self.runtime():
            for changes in [dict(schema='unknown'),dict(blas_threads=4),dict(blas_threads=True)]:
                with self.assertRaises(ValueError):
                    authenticate_environment(gpu_runtime=dict(self.args,**changes))
            with patch.object(validated, 'threadpool_info', return_value=[{'num_threads':4}]):
                with self.assertRaisesRegex(ValueError,'BLAS'):
                    authenticate_environment(gpu_runtime=self.args)

    def test_cli_resolves_new_receipt_paths(self):
        from bsfm.sampler.run import run_recipe
        root = self.fixture.root
        gpu = dict(self.args)
        for key in ('installation','validation','validation_plan','libdevice'):
            gpu[key] = Path(gpu[key]).relative_to(root).as_posix()
        recipe = dict(schema='bsfm.sampler-run.v1',backend='gpu',model='deep',chain_id='test',
            factor_ids=['a'],seed=1,files={},dataset_recipe=None,gpu_runtime=gpu,
            phases=[dict(run_id='production',warmup_steps=20,sweeps=1,save_every=1)])
        path = root/'recipe.json'; path.write_text(json.dumps(recipe))
        class Inspected(Exception): pass
        def inspect(*,gpu_runtime):
            for key in ('installation','validation','validation_plan','libdevice'):
                self.assertEqual(gpu_runtime[key], str(Path(self.args[key]).resolve()))
            raise Inspected()
        with patch('bsfm.sampler.run.check_repository'), \
                patch('bsfm.sampler.run_inputs.authenticate_environment', side_effect=inspect):
            with self.assertRaises(Inspected):run_recipe(path,root/'output',commit='a'*40)


if __name__ == '__main__': unittest.main()
