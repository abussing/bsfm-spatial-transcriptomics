"""Local single-writer publication primitives; no stochastic authority in ledgers."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path
import stat
import tempfile
import numpy as np
from .checkpoint_rng import json_text, parse_json


def safe(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        if p.exists() or p.is_symlink():
            s=p.lstat()
            if p.is_symlink() or getattr(s,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):
                raise ValueError('Reparse/symlink paths unsupported')
    return path


def file_record(path):
    p=safe(path)
    with p.open('rb') as f:sha=hashlib.file_digest(f,'sha256').hexdigest()
    return dict(bytes=p.stat().st_size,sha256=sha)


def read_json(path):return parse_json(safe(path).read_text(encoding='utf-8'))


def write_json(path,value):
    with safe(path).open('x',encoding='utf-8',newline='\n') as f:
        f.write(json_text(value)+'\n');f.flush();os.fsync(f.fileno())


def write_npz(path,arrays):
    with safe(path).open('xb') as f:
        np.savez_compressed(f,**arrays);f.flush();os.fsync(f.fileno())


def publish(source,destination):
    source=safe(source);destination=safe(destination)
    if destination.exists():raise FileExistsError(destination)
    if source.stat().st_dev!=destination.parent.stat().st_dev:raise ValueError('Cross-filesystem publication')
    if os.name=='posix':
        from .run_linux_storage import rename_noreplace
        rename_noreplace(source,destination)
    else:
        os.rename(source,destination)


def copy_exact(source,destination):
    """No hard links or overwrite; preserve any failed projection candidate."""
    source=safe(source);destination=safe(destination)
    if destination.exists():
        if file_record(source)!=file_record(destination):raise ValueError('Conflicting projection')
        return
    fd,name=tempfile.mkstemp(prefix='.attempt-',dir=destination.parent)
    with os.fdopen(fd,'wb') as out,source.open('rb') as inp:
        import shutil
        shutil.copyfileobj(inp,out);out.flush();os.fsync(out.fileno())
    if file_record(name)!=file_record(source):raise ValueError('Projection copy mismatch')
    publish(name,destination)


def advisory(path,value):
    path=safe(path);fd,name=tempfile.mkstemp(prefix='.attempt-ledger-',dir=path.parent)
    with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as f:
        f.write(json_text(value)+'\n');f.flush();os.fsync(f.fileno())
    os.replace(name,path)


@contextmanager
def writer(root):
    """OS-held exclusive lock, released on process death; no PID guessing."""
    if os.name=='nt':
        import msvcrt
        acquire=lambda f:msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
        release=lambda f:msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
    elif os.name=='posix':
        import fcntl
        acquire=lambda f:fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        release=lambda f:fcntl.flock(f.fileno(),fcntl.LOCK_UN)
    else:raise RuntimeError('Unsupported writer-lock platform')
    root=safe(root);root.mkdir(parents=True,exist_ok=True)
    with safe(root/'writer.lock').open('a+b') as f:
        f.seek(0,2)
        if f.tell()==0:f.write(b'0');f.flush()
        f.seek(0)
        try:acquire(f)
        except OSError as exc:raise RuntimeError('Another local writer owns the run') from exc
        try:yield
        finally:f.seek(0);release(f)
