"""Periodic checkpoint codec: fixed spectral arrays come from bound geometry.

The original Layer-7 payload and every array descriptor remain authoritative.
Only redundant spectral array bytes are omitted on disk. The full chart is
already preserved in the segment genesis; reconstruction verifies every hash.
"""
import numpy as np
from .checkpoint import _payload, _validate_payload
from .run_storage import write_npz

FORMAT = 'bsfm.compact-checkpoint.v1'


def load_compact(path, *, target, contract, migration_boundary_audit=None):
    with np.load(path, allow_pickle=False) as source:
        if len(source.files) != len(set(source.files)):
            raise ValueError('Duplicate checkpoint members')
        data = {k: source[k].copy(order='K') for k in source.files}
    marker = data.pop('compact_format', None)
    if marker is None or marker.shape != () or str(marker) != FORMAT:
        raise ValueError('Compact checkpoint format mismatch')
    if any(k.startswith('spectral_') for k in data):
        raise ValueError('Unexpected embedded spectral data')
    data.update({'spectral_'+k: np.array(v, copy=True, order='K')
                 for k, v in target.geometry.spectral.items() if k != 'audit'})
    return _validate_payload(data, target, contract, migration_boundary_audit=migration_boundary_audit)


def save_compact(path, **kwargs):
    data = _payload(**kwargs)
    data = {k: v for k, v in data.items() if not k.startswith('spectral_')}
    data['compact_format'] = np.array(FORMAT)
    write_npz(path, data)
    return load_compact(path, target=kwargs['target'], contract=kwargs['contract'])
