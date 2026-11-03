"""Read-only authentication of the two already accepted preparation environments.

No discovery, installation, mutation or runtime sampler bridge. This module uses
only the standard library so package authentication precedes numerical imports.
"""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import site
import sys
import zipfile

REPO = Path(__file__).resolve().parents[3]


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def record(path):
    p = Path(path)
    return dict(path=str(p.resolve()), bytes=p.stat().st_size, sha256=sha(p))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def authenticate(kind):
    require(kind in ('preparation', 'gpinit'), 'Unknown environment role')
    root = Path(sys.prefix).resolve()
    require(sys.version.split()[0] == '3.12.0', 'Unaccepted Python version')
    require(site.ENABLE_USER_SITE is False, 'User site must be disabled')
    require('include-system-site-packages = false' in (root/'pyvenv.cfg').read_text(),
            'System site fallback')
    if kind == 'preparation':
        lp = REPO/'environment/mesh/python-source-lock.json'
        lock = json.loads(lp.read_text())
        rp = REPO/'environment/mesh/runtime-lock.json'
        runtime = json.loads(rp.read_text())
        records = [runtime['python_base'], runtime['python_venv'],
                   *runtime['python_base_companions']]
        packages = {w['package']: w['version'] for w in lock['wheels']}
        require(Path(sys.executable).resolve() == Path(lock['python']['path']).resolve(),
                'Unaccepted preparation interpreter')
    else:
        lp = REPO/'environment/gpinit/source-lock.json'
        lock = json.loads(lp.read_text())
        rp = lp
        records = [lock['base_identity'], *lock['base_companions']]
        packages = {w['name']: w['version'] for w in lock['packages']}
        require(Path(sys.executable).resolve() == Path(lock['isolated_executable']).resolve(),
                'Unaccepted GPINIT interpreter')
        installed = root.parent/'installation.json'
        require(sha(installed) == lock['installation_report_sha256'], 'Installation receipt')
    for r in records:
        require(sha(r['path']) == r['sha256'] and Path(r['path']).stat().st_size == r['bytes'],
                'Runtime identity: '+r['path'])
    norm = lambda name: name.lower().replace('_', '-')
    expected = {norm(k): v for k, v in packages.items()} | {'pip': '23.2.1'}
    distributions = list(metadata.distributions())
    actual = {norm(d.metadata['Name']): d.version for d in distributions}
    require(actual == expected and len(distributions) == len(expected), 'Package closure mismatch')
    count = 0
    for d in distributions:
        base = Path(d.locate_file('')).resolve()
        require(base == root/'Lib/site-packages', 'Package outside isolated library')
        # Installed RECORD hashes establish internal integrity; they are not
        # independently authenticated wheel content in the GPINIT environment.
        text = d.read_text('RECORD')
        require(text is not None, 'Missing installed RECORD')
        for name, digest, size in csv.reader(text.splitlines()):
            if not digest:
                continue
            algorithm, value = digest.split('=', 1)
            require(algorithm == 'sha256', 'Unsupported RECORD algorithm')
            p = Path(d.locate_file(name)).resolve()
            require(p.is_relative_to(root), 'Installed file outside environment')
            measured = base64.urlsafe_b64encode(bytes.fromhex(sha(p))).decode().rstrip('=')
            require(measured == value and p.stat().st_size == int(size), 'Installed file changed: '+name)
            count += 1
    wheel_count = 0
    if kind == 'preparation':
        for w in lock['wheels']:
            require(sha(w['path']) == w['sha256'] and Path(w['path']).stat().st_size == w['bytes'],
                    'Authenticated cached wheel changed')
            with zipfile.ZipFile(w['path']) as archive:
                for name in archive.namelist():
                    if name.endswith('/') or name.endswith('.dist-info/RECORD'):
                        continue
                    require('.data/' not in name and '..' not in Path(name).parts,
                            'Unrecognized wheel layout')
                    p = root/'Lib/site-packages'/name
                    require(sha(p) == hashlib.sha256(archive.read(name)).hexdigest(),
                            'Installed file differs from authenticated wheel: '+name)
                    wheel_count += 1
    return dict(schema='bsfm.preparation-environment-check.v1', role=kind,
                executable=record(sys.executable), python=sys.version, packages=actual,
                lock=record(lp), runtime_lock=record(rp), runtime_files=records,
                installed_record_files_checked=count,
                authenticated_wheel_files_checked=wheel_count,
                user_site=False, system_site=False, status='pass',
                limitation=None if kind == 'preparation' else
                'Installed RECORD integrity and accepted install/source lock; cached wheel byte comparison not performed')
