"""Candidate GPU numerical/controller checks; never grants production admission."""
import sys

# -I ignores PYTHONDONTWRITEBYTECODE. Keep authenticated wheel caches unchanged.
sys.dont_write_bytecode = True

import argparse
import base64
import csv
import hashlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import site
import subprocess
import traceback
import unittest

ROOT = Path(__file__).resolve().parents[2]
TESTS = (
    'test_gpu_acceptance_roundoff.GPUAcceptanceRoundoff',
    'test_meeting_extensions.MeetingExtensions',
    'test_flat_range.FlatRangeTests',
    'test_sampler_layer4.Layer4Tests.test_centered_independent_full_precision_density_and_gradient',
    'test_sampler_layer4.Layer4Tests.test_precision_and_block_preconditioner_independent_dense',
    'test_sampler_layer4.Layer4Tests.test_draw_matches_dense_algebra_identical_innovations',
)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--installation', type=Path, required=True)
    p.add_argument('--installation-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--installation-only', action='store_true',
                   help='Check installation integrity without importing JAX or using a GPU')
    args = p.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('Validation output must be outside the repository')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema='bsfm.candidate-gpu-validation.v1', status='FAIL',
                  source_commit=args.commit, production_admitted=False,
                  scope='Synthetic numerical and controller checks; no production CLI admission or scientific fit')
    try:
        if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip() != args.commit:
            raise ValueError('Wrong source commit')
        if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
            raise ValueError('Dirty source checkout')
        if sha(args.installation) != args.installation_sha256:
            raise ValueError('Installation receipt changed')
        receipt = json.loads(args.installation.read_text())
        if (receipt['schema'] != 'bsfm.candidate-gpu-install.v1'
                or receipt['lock_sha256'] != sha(Path(__file__).with_name('requirements.lock'))
                or receipt['python'] != sys.version or receipt['python_sha256'] != sha(sys.executable)
                or Path(receipt['prefix']).resolve() != Path(sys.prefix).resolve()
                or site.ENABLE_USER_SITE):
            raise ValueError('Candidate installation identity mismatch')
        norm = lambda s: s.lower().replace('_', '-').replace('.', '-')
        distributions = list(metadata.distributions())
        actual = {norm(d.metadata['Name']): d.version for d in distributions}
        if actual != receipt['packages'] or len(actual) != len(distributions):
            raise ValueError('Package closure changed')
        prefix = Path(sys.prefix).resolve()
        records = {}
        checked = 0
        for d in distributions:
            for f in d.files or []:
                path = Path(d.locate_file(f))
                if str(f).endswith('.dist-info/RECORD'):
                    records[str(path.relative_to(prefix))] = sha(path)
            for name, digest, size in csv.reader(d.read_text('RECORD').splitlines()):
                if not digest:
                    continue
                path = Path(d.locate_file(name)).resolve()
                algorithm, expected = digest.split('=', 1)
                if not path.is_relative_to(prefix) or algorithm != 'sha256':
                    raise ValueError('Foreign package payload or unsupported digest')
                measured = base64.urlsafe_b64encode(bytes.fromhex(sha(path))).decode().rstrip('=')
                if measured != expected or path.stat().st_size != int(size):
                    raise ValueError('Installed package payload changed: ' + name)
                checked += 1
        if records != receipt['record_hashes']:
            raise ValueError('Package RECORD files changed')
        report.update(installation_sha256=args.installation_sha256, payload_files_checked=checked)
        if args.installation_only:
            report.update(status='INSTALLATION_VERIFIED',
                          scope='Installation identity and payload checks only; no numerical execution')
            return
        os.environ.update(JAX_PLATFORMS='cuda,cpu', JAX_ENABLE_X64='true',
                          BSFM_EXPERIMENTAL_CUDA='1', OPENBLAS_NUM_THREADS='1',
                          MKL_NUM_THREADS='1', OMP_NUM_THREADS='1',
                          XLA_PYTHON_CLIENT_PREALLOCATE='false')
        sys.path[:0] = [str(ROOT/'src'), str(ROOT/'tests')]
        import jax
        import jax.numpy as jnp
        import numpy as np
        from bsfm.sampler.run_gpu_environment import preflight_gpu_callback
        from sampler_layer3_support import system, dense_target
        if jax.default_backend() != 'gpu' or len(jax.devices()) != 1 or not jax.config.x64_enabled:
            raise ValueError('One allocated GPU and float64 required')
        report.update(device_kind=jax.devices()[0].device_kind, callback=preflight_gpu_callback())
        target, state, position = system()
        value, gradient, _ = target.value_grad(position, state, state_factor_ids=target.factor_ids)
        reference, refgrad = jax.value_and_grad(
            lambda x: dense_target(target, state, position, x))(jnp.asarray(position.values))
        np.testing.assert_allclose(value, reference, rtol=1e-10, atol=1e-10)
        np.testing.assert_allclose(gradient, refgrad, rtol=1e-9, atol=1e-9)
        report['deep_dense_oracle'] = dict(value_error=float(abs(value-reference)),
                                         gradient_max_error=float(np.max(np.abs(gradient-refgrad))))
        suite = unittest.defaultTestLoader.loadTestsFromNames(TESTS)
        expected_count = suite.countTestCases()
        with (output/'tests.log').open('w') as log:
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
        report.update(tests_run=result.testsRun, expected_tests=expected_count,
                      failures=[(str(t), detail) for t, detail in result.failures],
                      errors=[(str(t), detail) for t, detail in result.errors],
                      skipped=[(str(t), reason) for t, reason in result.skipped])
        if not result.wasSuccessful() or result.skipped or result.testsRun != expected_count:
            raise ValueError('Candidate GPU checks did not all pass; see tests.log')
        jax.effects_barrier()
        report['status'] = 'PASS'
    except BaseException:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
        print(json.dumps({k: report[k] for k in ('status', 'scope', 'production_admitted')}), flush=True)


if __name__ == '__main__':
    main()
