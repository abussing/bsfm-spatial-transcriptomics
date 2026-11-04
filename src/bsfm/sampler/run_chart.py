"""Proposed saved-chart reader. Validate the saved basis without an eigensolve.

Review-only API extension; does not change accepted Layer-2 numerical kernels.
"""
import copy
import hashlib
import json
from types import MappingProxyType
import numpy as np
from scipy.special import logsumexp
from bsfm.sampler.warp import WarpGeometry, mesh_identity, BINOM, NORMCONST, NU_U, D_FEM
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.checkpoint_rng import parse_json
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.retained_records import descriptor
from bsfm.sampler.run_storage import safe


def geometry_from_genesis(data, expected, path):
    """Pre-target read; full genesis/RNG validation still follows in the controller."""
    with np.load(safe(path),allow_pickle=False) as z:
        if len(z.files)!=len(set(z.files)):raise ValueError('Duplicate genesis array')
        arrays={k:z[k].copy(order='K') for k in z.files}
    metadata=arrays.pop('metadata')
    if metadata.shape!=() or metadata.dtype.kind!='U':raise ValueError('Genesis metadata encoding')
    record=parse_json(str(metadata))
    if (record['schema']!='bsfm.pre-sweep-endpoint.v1'
            or record['logical_sha256']!=digest({k:v for k,v in record.items() if k!='logical_sha256'})
            or {k:descriptor(v) for k,v in arrays.items()}!=record['arrays']):
        raise ValueError('Saved genesis integrity')
    contract=parse_json(record['contract'])
    if digest(contract)!=record['contract_sha256'] or parse_json(contract['geometry_identity'])!=expected:
        raise ValueError('Saved genesis geometry binding')
    chart={k.removeprefix('spectral_'):v for k,v in arrays.items() if k.startswith('spectral_')}
    for k in ('log_kappa_constant','log_trace_mass','log_reference_variance'):
        if chart[k].shape!=():raise ValueError('Saved chart scalar shape')
        chart[k]=chart[k].item()
    chart['audit']=record['spectral_audit']
    return restore_geometry(data,expected,chart,contract['spectral_identity'])


def restore_geometry(data, expected, saved, expected_spectral_identity):
    arrays={k:np.array(v,copy=True,order='K') for k,v in data.items()}
    actual=mesh_identity(arrays,section=expected['section'],mesh_sha256=expected['mesh_sha256'])
    if actual!=expected:raise ValueError('Restored geometry input identity mismatch')
    chart=copy.deepcopy(dict(saved))
    signature=json.dumps({k:logical_hash(v) if isinstance(v,np.ndarray) else v
                          for k,v in chart.items()},sort_keys=True)
    if signature!=expected_spectral_identity:raise ValueError('Saved spectral identity mismatch')
    fields={'U','projected_modes','modal_diagonals','log_modal_diagonals',
            'log_coefficients','powers','log_kappa_constant','log_trace_mass',
            'log_reference_variance','audit'}
    if set(chart)!=fields:raise ValueError('Saved spectral fields mismatch')
    terms=arrays['terms'];mass=terms[0];n=len(mass);u=np.asarray(chart['U'])
    if u.shape!=(n,n) or u.dtype!=np.float64 or not np.isfinite(u).all():
        raise ValueError('Invalid saved full-mode basis')
    modal=np.asarray(chart['modal_diagonals'])
    if (modal.shape!=(len(terms),n) or modal.dtype!=np.float64
            or not np.isfinite(modal).all() or np.any(modal<0)):
        raise ValueError('Invalid saved nonnegative modal diagonals')
    def relative(a,b):
        return np.linalg.norm(a-b)/max(np.finfo(float).tiny,np.linalg.norm(b))
    # Same residual thresholds as the accepted full-mode construction.
    tolerance=2e-10
    gram=u.T@mass@u
    if relative(gram,np.eye(n))>tolerance:raise ValueError('Saved mass orthogonality')
    transformed=[u.T@m@u for m in terms]
    diagonals=[]
    for matrix in transformed:
        d=np.diag(matrix).copy()
        if relative(matrix,np.diag(d))>tolerance:raise ValueError('Saved simultaneous diagonalization')
        if d.min() < -2e-12*max(1.,float(np.abs(d).max())):
            raise ValueError('Saved negative FEM mode')
        diagonals.append(np.maximum(d,0.))
    eigenvalues=np.diag(transformed[1])/np.diag(gram)
    if relative(terms[1]@u,mass@(u*eigenvalues))>tolerance:
        raise ValueError('Saved eigen residual')
    diagonal=np.stack(diagonals)
    if np.any(np.sum(diagonal>0,axis=0)==0):raise ValueError('Saved zero-precision mode')
    # These are independent algebraic geometry checks, not relaxed checkpoint
    # equality: the saved arrays remain byte-identical and define the target.
    derived={'projected_modes':arrays['projector']@u,'modal_diagonals':diagonal,
             'log_coefficients':np.log(NORMCONST*np.asarray(BINOM)),
             'powers':D_FEM-2.*np.arange(len(terms)),
             'log_kappa_constant':.5*np.log(8.*NU_U),
             'log_trace_mass':np.log(np.trace(mass))}
    for name,value in derived.items():
        got=np.asarray(chart[name]);value=np.asarray(value)
        if got.shape!=value.shape or not np.isfinite(got).all() or relative(got,value)>tolerance:
            raise ValueError('Saved chart geometry mismatch: '+name)
    # Internal formula bindings use exact saved modal data, not recomputed data.
    d=np.asarray(chart['modal_diagonals'])
    logs=np.full_like(d,-np.inf);positive=d>0;logs[positive]=np.log(d[positive])
    if not np.array_equal(logs,chart['log_modal_diagonals']):raise ValueError('Saved modal logarithms')
    variance=float(logsumexp(-logsumexp(chart['log_coefficients'][:,None]
        +chart['powers'][:,None]*chart['log_kappa_constant']+logs,axis=0))-chart['log_trace_mass'])
    if not np.isclose(variance,chart['log_reference_variance'],rtol=0,atol=tolerance):
        raise ValueError('Saved diagnostic variance')
    audit=chart['audit']
    if audit['status']!='PASS' or audit['n_v']!=n or not audit['full_rank_no_truncation']:
        raise ValueError('Saved full-mode audit')
    for field,label in [('U','basis_sha256'),('modal_diagonals','modal_diagonals_sha256'),
                        ('projected_modes','projected_modes_sha256')]:
        h=hashlib.sha256(np.ascontiguousarray(chart[field]).view(np.uint8)).hexdigest()
        if h!=audit[label]:raise ValueError('Saved chart audit hash')
    for values in (arrays,chart):
        for value in values.values():
            if isinstance(value,np.ndarray):value.flags.writeable=False
    restored=WarpGeometry(MappingProxyType(arrays),json.dumps(actual,sort_keys=True),
                          MappingProxyType(chart),signature)
    restored.validate()
    return restored
