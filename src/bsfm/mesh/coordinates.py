import numpy as np
from .identities import require, logical

SCALE = 6532.1214803230505


def transform(raw):
    raw = np.asarray(raw)
    require(raw.dtype == np.float64 and raw.ndim == 2 and raw.shape[1] == 2, 'Expected float64 N by 2 coordinates')
    require(len(raw) >= 3 and np.isfinite(raw).all(), 'Invalid coordinates')
    origin = raw.min(axis=0)
    numerical = (raw-origin)/SCALE
    return numerical, dict(origin=origin.tolist(), scale=SCALE, axis_order=['center_y','center_x'],
        units='source_native', physical_units='not_found', inverse='x=scale*z+origin',
        raw_hash=logical(raw), numerical_hash=logical(numerical))


def inverse(numerical, metadata):
    return np.asarray(numerical)*metadata['scale']+np.array(metadata['origin'])
