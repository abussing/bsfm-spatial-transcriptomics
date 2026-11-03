"""Explicit GPU execution entry using the recorded, tested existing HPC environment."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import os
from pathlib import Path
import site
import sys

import jax
from threadpoolctl import threadpool_info

from experiment import run, CONFIGS
from bsfm.sampler.run_storage import file_record, read_json

RECEIPT=Path(__file__).with_name('GPU_RUNTIME_RECEIPT.json')
PREFIX=Path('/work/abussing/arka_trying_gpu_again/env')
CORE={'numpy','scipy','jax','jaxlib','jax-cuda12-plugin','jax-cuda12-pjrt','blackjax',
      'jaxopt','optax','ml-dtypes','opt-einsum','absl-py','typing-extensions',
      'fastprogress','fastcore','threadpoolctl','nvidia-cudnn-cu12'}

def authenticate_gpu_environment():
    expected=read_json(RECEIPT)
    if (Path(sys.prefix).resolve()!=PREFIX or sys.version!=expected['python'] or site.ENABLE_USER_SITE
        or jax.default_backend()!='gpu' or not jax.config.x64_enabled
        or os.environ.get('BSFM_EXPERIMENTAL_CUDA')!='1'):
        raise ValueError('Recorded GPU/x64 environment required')
    devices=jax.devices()
    if len(devices)!=1 or 'V100' not in devices[0].device_kind:
        raise ValueError('One allocated V100 required')
    distributions=list(metadata.distributions())
    if {d.metadata['Name']:d.version for d in distributions}!=expected['packages']:
        raise ValueError('GPU package versions changed')
    for p,h in [(Path(sys.executable).resolve(),expected['python_sha256']),
                (Path('/work/apps/cuda/12.3/nvvm/libdevice/libdevice.10.bc'),expected['libdevice_sha256'])]:
        if file_record(p)['sha256']!=h:raise ValueError('GPU runtime binary changed')
    installed=PREFIX/'lib/python3.11/site-packages'
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
            actual=file_record(p)
            if actual['bytes']!=int(size) or base64.urlsafe_b64encode(bytes.fromhex(actual['sha256'])).decode().rstrip('=')!=value:
                raise ValueError('GPU installed numerical file changed: '+str(p))
            count+=1
    blas=threadpool_info()
    if any(p['num_threads']!=1 for p in blas):raise ValueError('One BLAS thread required')
    return dict(schema='bsfm.meeting-gpu-environment.v1',lock=file_record(RECEIPT),
                backend='gpu',x64=True,device_kind=devices[0].device_kind,
                packages=expected['packages'],installed_numerical_files=count,
                limitation='Existing shared environment; recorded package inventory and numerical RECORD integrity. GPU trajectories are not CPU-exact continuations.')

if __name__=='__main__':
    config,prepared,output,model,commit=sys.argv[1:]
    if config not in CONFIGS or model not in ('deep','flat'):raise ValueError('Unknown run configuration')
    print('GPU SCIENTIFIC RUN',config,model,'K=12 L=14',flush=True)
    run(config,Path(prepared),Path(output),model,commit,runtime_auth=authenticate_gpu_environment)
