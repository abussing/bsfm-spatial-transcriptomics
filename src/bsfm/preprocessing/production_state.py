"""Durable run metadata, exclusive process locking and bounded attempt cleanup."""
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import time
import uuid

from .raw_preflight import require


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path, value, *, replace=True):
    path = Path(path)
    require(replace or not path.exists(), 'Refusing to overwrite final metadata')
    temporary = path.with_name('.' + path.name + '.' + uuid.uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    # Windows scanners can briefly hold the destination open without delete sharing.
    # Retry only this atomic rename; never truncate or rewrite the previous checkpoint.
    for retry in range(5):
        try:
            os.replace(temporary, path)
            break
        except PermissionError as exc:
            if os.name != 'nt' or getattr(exc, 'winerror', None) not in (5, 32, 33) or retry == 4:
                raise
            time.sleep(0.05 * 2**retry)
    with path.open('r+b') as stream:
        os.fsync(stream.fileno())
    if os.name != 'nt':
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def plain_directory(path):
    """Reject symbolic links/junctions in any existing ancestor."""
    path = Path(path).absolute()
    for p in (path, *path.parents):
        require(not p.is_symlink() and not getattr(p, 'is_junction', lambda: False)(),
                'Linked directory is not permitted')
    return path.resolve()


def layout(root):
    root = plain_directory(root)
    root.mkdir(parents=True, exist_ok=True)
    for name in ('sections', 'attempts', 'receipts'):
        plain_directory(root / name).mkdir(exist_ok=True)
    require((root/'sections').stat().st_dev == (root/'attempts').stat().st_dev,
            'Attempts and sections must share a filesystem')
    return root


@contextmanager
def run_lock(root):
    """Kernel lock is released on process death; the lock file is never a completion flag."""
    path = Path(root)/'run.lock'
    require(not path.is_symlink(), 'Linked lock file')
    with path.open('a+b') as stream:
        if stream.seek(0, os.SEEK_END) == 0:
            stream.write(b'0'); stream.flush()
        stream.seek(0)
        if os.name == 'nt':
            import msvcrt
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == 'nt':
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


def new_attempt(root, section):
    require('/' not in section and '\\' not in section and section not in ('.', '..'), 'Invalid section')
    parent = plain_directory(Path(root)/'attempts')
    p = parent / ('.attempt-' + section + '-' + uuid.uuid4().hex)
    p.mkdir()
    return p


def contained_attempt(root, attempt):
    parent = plain_directory(Path(root)/'attempts')
    p = plain_directory(attempt)
    require(p.parent == parent and p.name.startswith('.attempt-'), 'Attempt cleanup outside run attempts')
    return p


def cleanup_attempt(root, attempt):
    p = contained_attempt(root, attempt)
    if not p.exists():
        return 'already_absent'
    require(not (p/'failure.json').exists(), 'Failed attempt must be retained')
    # Check all descendants before recursive deletion, including Windows reparse points.
    for child in p.rglob('*'):
        require(not child.is_symlink() and not getattr(child, 'is_junction', lambda: False)(),
                'Linked attempt descendant; cleanup refused')
        require(child.resolve().is_relative_to(p), 'Attempt descendant escaped containment')
    shutil.rmtree(p)
    return 'removed'
