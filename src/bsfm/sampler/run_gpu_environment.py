"""Shared GPU runtime authentication recovered from the reviewed S10 adapter.

Deployment paths are explicit; numerical package checks and device scope retain
that adapter's requirements. See WORKFLOW_GUIDE.md for provenance and limits.
"""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import importlib.util
import marshal
import os
from pathlib import Path
import site
import sys

import jax
import jax.numpy as jnp
import numpy as np
from threadpoolctl import threadpool_info

from .run_storage import file_record, read_json
from .split_kernels import gpu_acceptance_roundoff

CORE={'numpy','scipy','jax','jaxlib','jax-cuda12-plugin','jax-cuda12-pjrt','blackjax',
      'jaxopt','optax','ml-dtypes','opt-einsum','absl-py','typing-extensions',
      'fastprogress','fastcore','threadpoolctl','nvidia-cudnn-cu12'}
# Observed in the existing GPU environment, which passed the execution checks.
# BSFM uses JAX threefry and NumPy RNGs, not scipy.stats Sobol QMC.
ABSENT_UNUSED_RESOURCES={'scipy/stats/_sobol_direction_numbers.npz',
                        'docs/_static/blackjax.png','docs/examples/data/blackjax.png'}

def authenticate_gpu_environment(*, receipt, expected_sha256, prefix,
                                 site_packages, libdevice, p100_receipt=None,
                                 p100_sha256=None, blas_threads=1):
    """Authenticate the recorded GPU runtime using explicit deployment paths.

    No backend fallback or package installation. Receipts must be pinned by the
    caller's committed recipe. This retains the tested V100/P100 scope.
    """
    RECEIPT=Path(receipt).resolve(); PREFIX=Path(prefix).resolve()
    installed=Path(site_packages).resolve(); libdevice=Path(libdevice).resolve()
    if not installed.is_relative_to(PREFIX):
        raise ValueError('Site packages must be inside the declared prefix')
    if file_record(RECEIPT)['sha256']!=expected_sha256:
        raise ValueError('GPU runtime receipt changed')
    if type(blas_threads) is not int or blas_threads not in (1,4):
        raise ValueError('Explicit supported BLAS thread count must be 1 or 4')
    expected=read_json(RECEIPT)
    if (Path(sys.prefix).resolve()!=PREFIX or sys.version!=expected['python'] or site.ENABLE_USER_SITE
        or jax.default_backend()!='gpu' or not jax.config.x64_enabled
        or os.environ.get('BSFM_EXPERIMENTAL_CUDA')!='1'):
        raise ValueError('Recorded GPU/x64 environment required')
    devices=jax.devices()
    if len(devices)!=1:raise ValueError('One allocated GPU required')
    validation=RECEIPT
    if 'P100' in devices[0].device_kind:
        if p100_receipt is None or p100_sha256 is None:
            raise ValueError('Pinned P100 validation receipt required')
        validation=Path(p100_receipt).resolve()
        if file_record(validation)['sha256']!=p100_sha256:
            raise ValueError('P100 validation receipt changed')
        v=read_json(validation)
        if v['status']!='COMPLETED' or v['exit_code']!='0:0' or v['focused_tests_passed']!=4:
            raise ValueError('P100 execution validation required')
    elif 'V100' not in devices[0].device_kind:
        raise ValueError('Validated V100 or P100 required')
    distributions=list(metadata.distributions())
    if (len(distributions)!=len(expected['packages'])
        or {d.metadata['Name']:d.version for d in distributions}!=expected['packages']):
        raise ValueError('GPU package versions changed')
    for p,h in [(Path(sys.executable).resolve(),expected['python_sha256']),
                (libdevice,expected['libdevice_sha256'])]:
        if file_record(p)['sha256']!=h:raise ValueError('GPU runtime binary changed')
    observed={str(p.relative_to(installed)):file_record(p)['sha256'] for p in installed.glob('*.dist-info/RECORD')}
    if observed!=expected['record_hashes']:raise ValueError('Installed package records changed')
    count=0
    for d in distributions:
        if d.metadata['Name'].lower().replace('_','-') not in CORE:continue
        if Path(d.locate_file('')).resolve()!=installed:raise ValueError('Foreign numerical package')
        for name,h,size in csv.reader(d.read_text('RECORD').splitlines()):
            if not h:continue
            alg,value=h.split('=',1);p=Path(d.locate_file(name)).resolve()
            if alg!='sha256' or not p.is_relative_to(PREFIX):raise ValueError('Package path/hash invalid')
            # Historical installation omits package test fixtures. They are not
            # sampler runtime dependencies; numpy.testing itself remains checked.
            if 'tests' in Path(name).parts:continue
            if name in ABSENT_UNUSED_RESOURCES and not p.exists():continue
            actual=file_record(p)
            if actual['bytes']!=int(size) or base64.urlsafe_b64encode(bytes.fromhex(actual['sha256'])).decode().rstrip('=')!=value:
                # pip regenerates wheel-bundled bytecode for the install path.
                # Its source must itself have a hashed RECORD entry and match it.
                if p.suffix!='.pyc':raise ValueError('GPU installed numerical file changed: '+str(p))
                source=Path(importlib.util.source_from_cache(str(p)))
                source_name=str(source.relative_to(installed))
                source_rows=[r for r in csv.reader(d.read_text('RECORD').splitlines()) if r[0]==source_name]
                if len(source_rows)!=1 or not source_rows[0][1].startswith('sha256='):
                    raise ValueError('Regenerated bytecode lacks authenticated source')
                raw_source=source.read_bytes();sr=source_rows[0]
                if len(raw_source)!=int(sr[2]) or base64.urlsafe_b64encode(hashlib.sha256(raw_source).digest()).decode().rstrip('=')!=sr[1].split('=',1)[1]:
                    raise ValueError('Bytecode source changed')
                raw=p.read_bytes()
                if raw[:4]!=importlib.util.MAGIC_NUMBER:raise ValueError('Bytecode interpreter mismatch')
                actual_code=marshal.loads(raw[16:])
                optimization=2 if '.opt-2.' in p.name else 1 if '.opt-1.' in p.name else 0
                if actual_code!=compile(raw_source,actual_code.co_filename,'exec',dont_inherit=True,optimize=optimization):
                    raise ValueError('Bytecode does not match authenticated source')
            count+=1
    blas=threadpool_info()
    if not blas or any(p['num_threads']!=blas_threads for p in blas):
        raise ValueError('BLAS thread count differs from requested execution configuration')
    return dict(schema='bsfm.meeting-gpu-environment.v1',lock=file_record(RECEIPT),
                backend='gpu',x64=True,device_kind=devices[0].device_kind,
                device_validation=file_record(validation),
                packages=expected['packages'],installed_numerical_files=count,blas_threads=blas_threads,
                absent_unused_resources=sorted(ABSENT_UNUSED_RESOURCES),
                limitation='Existing shared environment; recorded inventory and numerical runtime RECORD integrity; package tests excluded. GPU trajectories are not CPU-exact continuations.')

def preflight_gpu_callback():
    """Exercise the existing GPU roundoff host callback before initialization."""
    if jax.default_backend()!='gpu':raise ValueError('GPU computation backend required')
    probe=jax.jit(gpu_acceptance_roundoff)(jnp.asarray([1+np.finfo(np.float64).eps],dtype=jnp.float64))
    probe.block_until_ready();jax.effects_barrier()
    if probe.device.platform!='gpu' or float(probe[0])!=1.:raise ValueError('GPU callback preflight failed')
    return dict(backend='gpu',device=str(probe.device),callback_passed=True)
