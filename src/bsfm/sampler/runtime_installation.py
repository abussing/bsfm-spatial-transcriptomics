"""Standard-library verification of an isolated, pinned GPU wheel installation."""
import base64
import csv
import hashlib
import importlib.metadata as metadata
import json
from pathlib import Path
import site
import sys


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify_installation(installation, expected_sha256, wheel_lock):
    """Check the same installation before validation and before sampler execution."""
    if sha(installation) != expected_sha256:
        raise ValueError('Installation receipt changed')
    receipt = json.loads(Path(installation).read_text())
    prefix = Path(sys.prefix).resolve()
    if (receipt['schema'] != 'bsfm.candidate-gpu-install.v1'
            or receipt['lock_sha256'] != sha(wheel_lock)
            or receipt['python'] != sys.version
            or receipt['python_sha256'] != sha(sys.executable)
            or Path(receipt['prefix']).resolve() != prefix
            or site.ENABLE_USER_SITE):
        raise ValueError('Candidate installation identity mismatch')
    norm = lambda s: s.lower().replace('_', '-').replace('.', '-')
    distributions = list(metadata.distributions())
    actual = {norm(d.metadata['Name']): d.version for d in distributions}
    if actual != receipt['packages'] or len(actual) != len(distributions):
        raise ValueError('Package closure changed')
    records = {}
    checked = 0
    for distribution in distributions:
        if not Path(distribution.locate_file('')).resolve().is_relative_to(prefix):
            raise ValueError('Foreign package installation')
        for f in distribution.files or []:
            path = Path(distribution.locate_file(f)).resolve()
            if Path(f).name == 'RECORD' and Path(f).parent.name.endswith('.dist-info'):
                records[str(path.relative_to(prefix))] = sha(path)
        for name, digest, size in csv.reader(distribution.read_text('RECORD').splitlines()):
            if not digest:
                continue
            path = Path(distribution.locate_file(name)).resolve()
            algorithm, expected = digest.split('=', 1)
            if not path.is_relative_to(prefix) or algorithm != 'sha256':
                raise ValueError('Foreign package payload or unsupported digest')
            measured = base64.urlsafe_b64encode(bytes.fromhex(sha(path))).decode().rstrip('=')
            if measured != expected or path.stat().st_size != int(size):
                raise ValueError('Installed package payload changed: ' + name)
            checked += 1
    if records != receipt['record_hashes']:
        raise ValueError('Package RECORD files changed')
    return receipt, checked
