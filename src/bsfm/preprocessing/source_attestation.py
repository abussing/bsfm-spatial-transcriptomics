"""Ephemeral raw-source authentication for one launcher process, never a cache file."""
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
import weakref

from .raw_preflight import require, sha256_file

_ACTIVE = weakref.WeakSet()


def stat_identity(path):
    s = Path(path).stat()
    return {k: getattr(s, k) for k in ('st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_dev', 'st_ino')}


@dataclass(frozen=True, eq=False)
class _Attestation:
    path: Path
    digest: str
    size: int
    initial_stat: tuple
    pid: int

    def record(self):
        return {'path': str(self.path), 'sha256': self.digest, 'bytes': self.size,
                'initial_stat': dict(self.initial_stat)}


def authenticate(path, expected):
    path = Path(path).resolve()
    before = stat_identity(path)
    require(before['st_size'] == expected['bytes'], 'Raw source size mismatch')
    digest = sha256_file(path)
    require(digest == expected['sha256'], 'Raw source fingerprint mismatch')
    require(stat_identity(path) == before, 'Source changed during authentication')
    return {'path': str(path), 'bytes': before['st_size'], 'sha256': digest,
            'initial_stat': before, 'authenticated_at': datetime.now(timezone.utc).isoformat()}


@contextmanager
def source_session(path, expected):
    """Only the launcher calls this; no CLI/persisted attestation is accepted."""
    start = authenticate(path, expected)
    token = _Attestation(Path(start['path']), start['sha256'], start['bytes'],
                         tuple(start['initial_stat'].items()), os.getpid())
    _ACTIVE.add(token)
    try:
        yield token, start
    finally:
        _ACTIVE.discard(token)


def check_attestation(token, path, expected):
    require(type(token) is _Attestation and token in _ACTIVE and token.pid == os.getpid(),
            'Source attestation must originate in this active launcher process')
    require(Path(path).resolve() == token.path and token.digest == expected['sha256']
            and token.size == expected['bytes'], 'Source attestation identity mismatch')
    require(stat_identity(path) == dict(token.initial_stat), 'Source stat changed since authentication')


def final_authentication(token, path, expected):
    check_attestation(token, path, expected)
    result = authenticate(path, expected)
    check_attestation(token, path, expected)
    return result
