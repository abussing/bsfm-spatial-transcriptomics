"""Read-only package/runtime/source and CPU library-isolation validation."""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import site
import struct
import sys

import jax
import numpy as np
from threadpoolctl import threadpool_info


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    here=Path(__file__).resolve().parent
    lock=json.loads((here/'source-lock.json').read_text())
    root=Path(sys.prefix).parent
    assert sys.version.split()[0]==lock['python']
    assert not site.ENABLE_USER_SITE
    assert sys.prefix!=sys.base_prefix
    assert jax.default_backend()=='cpu' and jax.config.x64_enabled
    normalize=lambda s:s.lower().replace('_','-')
    actual={normalize(d.metadata['Name']):d.version for d in importlib.metadata.distributions()}
    expected={'pip':lock['pip'],**{normalize(p['name']):p['version'] for p in lock['packages']}}
    assert actual==expected,(actual,expected)
    for runtime in lock['runtime']: assert sha(runtime['path'])==runtime['sha256']
    receipt=json.loads((root/'installed.json').read_text())
    # The first Windows acquisition used CRLF locks. Git's canonical text is
    # LF. Authenticate that precise reversible byte conversion, not arbitrary
    # JSON/whitespace equivalence; preserve original install hashes in receipt.
    transport={}
    for filename,field in [('source-lock.json','lock_sha256'),
                            ('requirements.lock.txt','requirements_sha256')]:
        data=(here/filename).read_bytes()
        assert b'\r' not in data, 'Canonical locks must use LF'
        exact=hashlib.sha256(data).hexdigest()
        crlf=hashlib.sha256(data.replace(b'\n',b'\r\n')).hexdigest()
        assert receipt[field] in (exact,crlf), 'Installation lock identity mismatch'
        transport[filename]=dict(canonical_LF_sha256=exact,installed_lock_sha256=receipt[field],
                                  difference='none' if receipt[field]==exact else 'LF/CRLF only')
    for w in receipt['wheels']:
        p=root/'wheels'/w['filename']
        assert p.stat().st_size==w['bytes'] and sha(p)==w['sha256']
    modules={}
    for name in ('jax','jaxlib','numpy','scipy','blackjax','jaxopt','optax','fastprogress'):
        p=Path(importlib.import_module(name).__file__).resolve()
        assert Path(sys.prefix).resolve() in p.parents
        modules[name]=str(p)
    record=dict(schema='bsfm.sampler-layer5-cpu-validation.v1',status='PASS',
        python=sys.version,executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,
        platform=platform.platform(),architecture=platform.machine(),pointer_bits=struct.calcsize('P')*8,
        packages=actual,modules=modules,user_site_enabled=site.ENABLE_USER_SITE,
        backend=jax.default_backend(),x64=jax.config.x64_enabled,devices=list(map(str,jax.devices())),
        thread_environment={x:os.environ.get(x) for x in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS')},
        blas=threadpool_info(),runtime=lock['runtime'],wheels=receipt['wheels'],
        source_lock_sha256=sha(here/'source-lock.json'),requirements_sha256=sha(here/'requirements.lock.txt'),
        build_receipt=receipt,lock_transport=transport,
        limitations=['Windows CPU only; not a CUDA/HPC or complete sampler environment'])
    args.output.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print('PASS: runtime, exact package set, wheels, CPU/x64 and module isolation')


if __name__=='__main__':main()
