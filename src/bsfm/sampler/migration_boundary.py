"""Audit a recomputed fitted-value digest only during explicit runtime migration."""
from contextlib import contextmanager
from contextvars import ContextVar


chart_migration_audit = ContextVar('bsfm_chart_migration_audit', default=None)


@contextmanager
def migration_chart_validation(audit):
    """Explicit migration lineage only; ordinary chart checks stay exact."""
    if audit is not None and not isinstance(audit,list):
        raise ValueError('Migration chart audit list required')
    token=chart_migration_audit.set(audit)
    try:
        yield
    finally:
        chart_migration_audit.reset(token)


def same_boundary(actual, saved, *, migration_audit=None):
    from .checkpoint_contract import require_hash
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
