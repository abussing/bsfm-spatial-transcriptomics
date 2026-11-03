"""Authenticate the recorded Linux build without substituting a Windows lock."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
from pathlib import Path
import platform
import site
import sys
import zipfile

from .run_storage import file_record, read_json

REPO = Path(__file__).resolve().parents[3]
RECEIPTS = REPO / 'docs/environment/layer9-linux-20261103'


def verify_wheel(wheel, expected, site_packages):
    if file_record(wheel) != {k: expected[k] for k in ('bytes', 'sha256')}:
        raise ValueError('Cached Linux wheel changed')
    count = 0
    with zipfile.ZipFile(wheel) as archive:
        for name in archive.namelist():
            if name.endswith('/') or name.endswith('.dist-info/RECORD'):
                continue
            if '.data/' in name:
                continue  # Installed RECORD authenticates platform script relocation.
            dest = (site_packages / name).resolve()
            if not dest.is_relative_to(site_packages):
                raise ValueError('Wheel member escapes site packages')
            if hashlib.sha256(archive.read(name)).hexdigest() != file_record(dest)['sha256']:
                raise ValueError('Installed Linux wheel member changed')
            count += 1
    return count


def authenticate_linux_environment():
    import jax
    from threadpoolctl import threadpool_info
    prefix = Path(sys.prefix).resolve()
    root = prefix.parent
    expected_report = RECEIPTS / 'job22013408-build-report.json'
    report = read_json(expected_report)
    package_report = RECEIPTS / 'job22013408-package-validation.json'
    packages = read_json(package_report)
    lockpath = REPO / 'docs/sampler/review-layer9-20261103/LINUX_ENVIRONMENT_PROPOSAL.json'
    if (platform.system(), platform.machine(), platform.python_version()) != ('Linux', 'x86_64', '3.11.14'):
        raise ValueError('Recorded Linux x86_64 Python 3.11.14 required')
    if (site.ENABLE_USER_SITE or sys.prefix == sys.base_prefix
            or 'include-system-site-packages = false' not in (prefix/'pyvenv.cfg').read_text()
            or not jax.config.x64_enabled or jax.default_backend() != 'cpu'):
        raise ValueError('Isolated Linux CPU/x64 environment required')
    if report['status'] != 'environment_restored_numerical_validation_pending':
        raise ValueError('Unverified Linux build receipt')
    if (file_record(root/'build-report.json') != file_record(expected_report)
            or file_record(root/'package-validation.json') != file_record(package_report)
            or file_record(package_report)['sha256'] != report['package_report_sha256']
            or file_record(lockpath)['sha256'] != report['runtime_lock_sha256']):
        raise ValueError('Linux build/lock receipt identity changed')
    if file_record((Path(sys.base_prefix)/'bin/python').resolve())['sha256'] != report['base_python_sha256']:
        raise ValueError('Linux base interpreter changed')
    if file_record(sys.executable)['sha256'] != report['base_python_sha256']:
        raise ValueError('Linux environment interpreter changed')
    distributions = list(metadata.distributions())
    actual = {d.metadata['Name'].lower().replace('_', '-'): d.version for d in distributions}
    if actual != packages['packages'] or len(distributions) != len(actual):
        raise ValueError('Linux installed package closure mismatch')
    site_packages = prefix/'lib/python3.11/site-packages'
    archives = {r['name']: r for r in report['archives']}
    wheel_files = 0
    for row in read_json(lockpath)['packages']:
        if row['name'] == 'ml_dtypes':
            wheel = report['built_wheel']
            path = root/'wheels'/wheel['name']
        else:
            filename = row['url'].rsplit('/', 1)[-1]
            wheel = archives[filename]
            if wheel['sha256'] != row['sha256']:
                raise ValueError('Linux archive differs from frozen lock')
            path = root/'archives'/filename
        wheel_files += verify_wheel(path, wheel, site_packages)
    installed_files = 0
    for distribution in distributions:
        if Path(distribution.locate_file('')).resolve() != site_packages:
            raise ValueError('Foreign Linux site package')
        for name, encoded, size in csv.reader(distribution.read_text('RECORD').splitlines()):
            if not encoded:
                continue
            alg, value = encoded.split('=', 1)
            path = Path(distribution.locate_file(name)).resolve()
            if alg != 'sha256' or not path.is_relative_to(prefix):
                raise ValueError('Linux installed RECORD path/hash')
            record = file_record(path)
            if (base64.urlsafe_b64encode(bytes.fromhex(record['sha256'])).decode().rstrip('=') != value
                    or record['bytes'] != int(size)):
                raise ValueError('Linux installed RECORD mismatch')
            installed_files += 1
    blas = threadpool_info()
    if any(row['num_threads'] != 1 for row in blas):
        raise ValueError('Single-thread numerical libraries required')
    return dict(schema='bsfm.layer9-linux-cpu-authentication.v1',
                executable=str(Path(sys.executable).resolve()),
                runtime=file_record(sys.executable), lock=file_record(lockpath),
                installed_receipt=file_record(expected_report), packages=actual,
                cpu=True, x64=True, blas=blas, installed_record_files=installed_files,
                wheel_member_files=wheel_files,
                limitation='Same-platform validation required; bootstrap pip/setuptools checked by installed RECORD')
