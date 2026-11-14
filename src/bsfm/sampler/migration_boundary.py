"""Audit a recomputed fitted-value digest only during explicit runtime migration."""
from .checkpoint_contract import require_hash


def same_boundary(actual, saved, *, migration_audit=None):
    if migration_audit is None:
        return actual == saved
    if not isinstance(migration_audit, list):
        raise ValueError('Migration boundary audit list required')
    key = 'fitted_Y_sha256'
    if key not in actual or key not in saved:
        return False
    require_hash(actual[key]); require_hash(saved[key])
    if {k:v for k,v in actual.items() if k != key} != {k:v for k,v in saved.items() if k != key}:
        return False
    # Original codecs store only this derived digest, not the fitted matrix.
    # Every underlying state array is authenticated exactly by the caller.
    # A source digest cannot bound floating-point error on another BLAS runtime.
    migration_audit.append(dict(quantity='fitted_Y_sha256',source=saved[key],
        destination=actual[key],equal=actual[key] == saved[key],
        interpretation='recomputed from exact authenticated loading and eta; no numerical error bound from a digest'))
    return True
