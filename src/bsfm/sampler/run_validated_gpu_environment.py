"""Opt-in runtime identity backed by pinned installation and GPU test evidence.

Legacy V100/P100 authentication and identities are deliberately unchanged.
This evidence establishes bounded execution checks, not scientific convergence.
"""
import json
import math
import os
from pathlib import Path

import jax
from threadpoolctl import threadpool_info

from .runtime_installation import verify_installation, sha
from .run_storage import file_record

SCHEMA = 'bsfm.validated-gpu-runtime.v1'
ROOT = Path(__file__).resolve().parents[3]


def authenticate_validated_gpu_environment(*, schema, installation,
        installation_sha256, validation, validation_sha256, validation_plan,
        validation_plan_sha256, libdevice, blas_threads):
    if schema != SCHEMA or type(blas_threads) is not int or blas_threads != 1:
        raise ValueError('Validated runtime schema and one tested BLAS thread required')
    if (jax.default_backend() != 'gpu' or not jax.config.x64_enabled
            or os.environ.get('BSFM_EXPERIMENTAL_CUDA') != '1'):
        raise ValueError('Validated GPU/x64 environment required')
    devices = jax.devices()
    if len(devices) != 1:
        raise ValueError('One allocated GPU required')
    if sha(validation) != validation_sha256 or sha(validation_plan) != validation_plan_sha256:
        raise ValueError('Pinned GPU validation evidence changed')
    result = json.loads(Path(validation).read_text())
    plan = json.loads(Path(validation_plan).read_text())
    if (result['schema'] != 'bsfm.candidate-gpu-validation.v1'
            or plan['schema'] != 'bsfm.external-runtime-validation-plan.v1'
            or result['status'] != 'PASS'
            or result['source_commit'] != plan['source_commit']
            or result['installation_sha256'] != installation_sha256
            or result['tests_run'] != 12 or result['expected_tests'] != 12
            or result['failures'] or result['errors'] or result['skipped']
            or result['device_kind'] != devices[0].device_kind
            or result['callback']['backend'] != 'gpu'
            or result['callback']['callback_passed'] is not True):
        raise ValueError('Complete matching GPU execution evidence required')
    oracle = result['deep_dense_oracle']
    if any(not math.isfinite(oracle[k]) or oracle[k] < 0 for k in ('value_error', 'gradient_max_error')):
        raise ValueError('Finite dense-oracle evidence required')
    lock = ROOT/'environment/sampler-gpu/requirements.lock'
    for key, path in [('installation', installation), ('wheel_lock', lock), ('libdevice', libdevice)]:
        if file_record(path) != {k: plan['artifact_records'][key][k] for k in ('bytes', 'sha256')}:
            raise ValueError('Validated runtime artifact changed: ' + key)
    receipt, count = verify_installation(installation, installation_sha256, lock)
    if count != result['payload_files_checked']:
        raise ValueError('Validated package payload count changed')
    blas = threadpool_info()
    if not blas or any(p['num_threads'] != blas_threads for p in blas):
        raise ValueError('BLAS thread count differs from tested runtime')
    return dict(schema=SCHEMA, lock=file_record(installation),
                validation=file_record(validation), validation_plan=file_record(validation_plan),
                libdevice=file_record(libdevice), backend='gpu', x64=True,
                device_kind=devices[0].device_kind, packages=receipt['packages'],
                installed_numerical_files=count, blas_threads=blas_threads,
                limitation='Bounded GPU execution evidence; no cross-runtime exact continuation or convergence claim')
