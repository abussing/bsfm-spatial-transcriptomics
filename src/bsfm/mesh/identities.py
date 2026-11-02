"""Explicit file and logical identities shared by mesh artifacts."""
import hashlib
import json
import os
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[3]


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    path = Path(path)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def file_record(path):
    p = Path(path)
    return dict(bytes=p.stat().st_size, sha256=sha(p))


def logical(array):
    a = np.asarray(array)
    require(a.dtype.kind in 'fiub', 'Unsupported logical dtype')
    a = np.ascontiguousarray(a.astype(a.dtype.newbyteorder('<'), copy=False))
    header = json.dumps(dict(shape=list(a.shape), dtype=a.dtype.str), sort_keys=True).encode()
    return hashlib.sha256(header+b'\n'+a.tobytes()).hexdigest()


def ordered_ids(values):
    digest=hashlib.sha256()
    for value in values:
        encoded=str(value).encode('utf-8')
        digest.update(len(encoded).to_bytes(8,'little'));digest.update(encoded)
    return digest.hexdigest()
