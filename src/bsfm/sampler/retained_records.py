"""Candidate encoding and independent closed-file retained-record validation."""
import hashlib
from pathlib import Path
import numpy as np
from .contracts import GaussianState, array, logical_hash
from .conjugate import compute_Yhat
from .field_target import FieldPosition
from .chart import validate_chart_state
from .layer4 import STATE_ARRAYS, state_hashes
from .layer6 import SweepResult
from .checkpoint_contract import digest, require_hash
from .checkpoint_rng import json_text, parse_json, exact_keys
from .retained_contract import RECORD_SCHEMA, validate_retained_contract, retain_at, count
from .retained_diagnostics import diagnostics_for, validate_diagnostics, encode

EXTRA = ('ell_eta','ell_U','sigma_U','W_cell','W_active','positions','permutation','sweep')
AUDIT_KEYS = ('schema','label','target_sha256','factor_ids','b_sigma2_sha256','state_before',
              'state_after','positions_before','positions_after','rng_before','rng_after','fitted_Y_sha256')


def descriptor(a):
    if not isinstance(a,np.ndarray) or a.dtype.hasobject:
        raise ValueError('Non-object arrays required')
    return dict(dtype=a.dtype.str, shape=list(a.shape), sha256=logical_hash(a))


def physical_arrays(target, positions):
    values = [target.features(p)[:2] for p in positions]
    return np.stack([v[0] for v in values]), np.stack([v[1] for v in values])


def validate_audit(audit, target, b_sigma2):
    exact_keys(audit, AUDIT_KEYS)
    if (audit['schema'] != 'bsfm.completed-sweep-audit.v1'
            or not isinstance(audit['label'],str) or not audit['label']
            or audit['target_sha256'] != hashlib.sha256(target.identity.encode()).hexdigest()
            or audit['factor_ids'] != list(target.factor_ids)
            or audit['b_sigma2_sha256'] != logical_hash(b_sigma2)):
        raise ValueError('Sweep identity/chronology mismatch')
    for name in ('state_before','state_after'):
        exact_keys(audit[name], STATE_ARRAYS)
        for x in audit[name].values(): require_hash(x)
    for name in ('positions_before','positions_after'):
        if len(audit[name]) != len(target.factor_ids): raise ValueError('Incomplete factor hashes')
        for x in audit[name]: require_hash(x)
    require_hash(audit['fitted_Y_sha256'])
    for name in ('rng_before','rng_after'):
        exact_keys(audit[name], ('numpy_global_sha256','eta_generator','eta_rng_sha256',
            'gauge_generator','gauge_rng_sha256','jax_impl','jax_key_data'))
        for key in ('numpy_global_sha256','eta_rng_sha256','gauge_rng_sha256'): require_hash(audit[name][key])


def pack(meta, arrays):
    meta = parse_json(json_text(meta))
    meta['arrays'] = {k:descriptor(v) for k,v in arrays.items()}
    meta['logical_sha256'] = digest(meta)
    return dict(arrays, metadata=np.array(json_text(meta)))


def make_completed(target, contract, b_sigma2, result, *, sweep, retained_index,
                   previous_sha256, events, elapsed_seconds):
    r = validate_retained_contract(contract,target,b_sigma2)
    if not isinstance(result,SweepResult): raise ValueError('Completed sweep required')
    retained = retain_at(r,sweep)
    count(retained_index,'retained index',int(retained))
    state=result.state; k=len(target.factor_ids)
    slices=state.validate(target.inputs,factors=k)
    validate_audit(result.audit,target,b_sigma2)
    if len(result.positions)!=k: raise ValueError('Missing positions')
    for i,p in enumerate(result.positions): validate_chart_state(target,p,state,i)
    if (state_hashes(state)!=result.audit['state_after']
            or [logical_hash(p.values) for p in result.positions]!=result.audit['positions_after']
            or logical_hash(compute_Yhat(state.loading,state.eta,slices))!=result.audit['fitted_Y_sha256']
            or logical_hash(result.fitted_Y)!=result.audit['fitted_Y_sha256']):
        raise ValueError('Incoherent completed state')
    arrays={}
    if retained:
        arrays={name:np.array(getattr(state,name),copy=True) for name in STATE_ARRAYS}
        wc,wa=physical_arrays(target,result.positions)
        arrays.update(ell_eta=np.asarray([v['ell_eta'] for v in result.warp_summaries],np.float64),
            ell_U=np.asarray([v['ell_W'] for v in result.warp_summaries],np.float64),
            sigma_U=np.asarray([v['sigma_W'] for v in result.warp_summaries],np.float64),
            W_cell=wc,W_active=wa,positions=np.stack([p.values for p in result.positions]),
            permutation=np.arange(k,dtype=np.int64),sweep=np.array(sweep,dtype=np.int64))
    meta=dict(schema=RECORD_SCHEMA,contract_sha256=contract.sha256,status='completed',
        sweep=sweep,production_sweep=max(0,sweep-r['retention']['settling_sweeps']),
        retained_index=retained_index if retained else None,
        previous_sha256=previous_sha256,diagnostics=diagnostics_for(result,events=events,elapsed_seconds=elapsed_seconds))
    return pack(meta,arrays)


def make_failure(contract, *, sweep, previous_sha256, events, partial_diagnostics):
    count(sweep,'attempted sweep',1)
    meta=dict(schema=RECORD_SCHEMA,contract_sha256=contract.sha256,status='failed',sweep=sweep,
        production_sweep=None,retained_index=None,previous_sha256=previous_sha256,
        diagnostics=encode(dict(events=events,last_completed_sweep=sweep-1,attempted_sweep=sweep,
                                partial_diagnostics=partial_diagnostics)))
    return pack(meta,{})


def load_record(path, *, target, contract, b_sigma2, migration_warp_audit=None):
    r=validate_retained_contract(contract,target,b_sigma2)
    with Path(path).open('rb') as stream:
        with np.load(stream,allow_pickle=False) as source:
            if len(source.files)!=len(set(source.files)): raise ValueError('Duplicate NPZ members')
            data={n:source[n].copy() for n in source.files}
    if 'metadata' not in data or data['metadata'].shape!=() or data['metadata'].dtype.kind!='U':
        raise ValueError('Scalar Unicode metadata required')
    m=parse_json(str(data.pop('metadata')))
    exact_keys(m, ('schema','contract_sha256','status','sweep','production_sweep','retained_index',
                  'previous_sha256','diagnostics','arrays','logical_sha256'))
    if (m['schema']!=RECORD_SCHEMA or m['contract_sha256']!=contract.sha256
            or m['logical_sha256']!=digest({k:v for k,v in m.items() if k!='logical_sha256'})):
        raise ValueError('Record schema/contract/hash mismatch')
    count(m['sweep'],'sweep',1);require_hash(m['previous_sha256'])
    if set(data)!=set(m['arrays']): raise ValueError('Missing/extra array')
    for n,a in data.items():
        if json_text(descriptor(a))!=json_text(m['arrays'][n]): raise ValueError('Array hash/shape/dtype mismatch: '+n)
    if m['status'] not in ('completed','failed'): raise ValueError('Unknown status')
    failed=m['status']=='failed'
    d=validate_diagnostics(m['diagnostics'],target.factor_ids,failed=failed)
    if failed:
        if (data or m['retained_index'] is not None or m['production_sweep'] is not None
                or d['last_completed_sweep']!=m['sweep']-1 or d['attempted_sweep']!=m['sweep']):
            raise ValueError('Failure falsely represented as completion')
        return m,data,d
    retained=retain_at(r,m['sweep'])
    expected=set(STATE_ARRAYS)|set(EXTRA) if retained else set()
    if set(data)!=expected: raise ValueError('Incomplete or unexpected retained state')
    if retained: count(m['retained_index'],'retained index',1)
    elif m['retained_index'] is not None: raise ValueError('Unexpected retained index')
    if type(m['production_sweep']) is not int or m['production_sweep']!=max(0,m['sweep']-r['retention']['settling_sweeps']):
        raise ValueError('Production chronology mismatch')
    validate_audit(d['sweep_audit'],target,b_sigma2)
    if retained:
        k=len(target.factor_ids);n=target.inputs.arrays['Y'].shape[1];a=len(target.geometry.arrays['active_indices'])
        state=GaussianState(**{v:data[v] for v in STATE_ARRAYS},input_identity_json=target.inputs.identity_json)
        slices=state.validate(target.inputs,factors=k)
        array(data['positions'],'positions',(k,target.position_dimension))
        positions=tuple(FieldPosition(data['positions'][i],fid,target.identity) for i,fid in enumerate(target.factor_ids))
        for i,p in enumerate(positions): validate_chart_state(target,p,state,i)
        for key in ('ell_eta','ell_U','sigma_U'): array(data[key],key,(k,),positive=True)
        array(data['W_cell'],'W_cell',(k,n,2));array(data['W_active'],'W_active',(k,a,2))
        if (data['sweep'].dtype!=np.int64 or data['sweep'].shape!=() or int(data['sweep'])!=m['sweep']
                or data['permutation'].dtype!=np.int64 or not np.array_equal(data['permutation'],np.arange(k))):
            raise ValueError('Native factor/sweep order corrupted')
        for i,row in enumerate(d['warp']):
            exact_keys(row,('factor_id','ell_eta','ell_W','sigma_W'))
            expected = target.hyperparameters(positions[i])
            if (row != dict(factor_id=target.factor_ids[i], **expected)
                    or data['ell_eta'][i]!=expected['ell_eta']
                    or data['ell_U'][i]!=expected['ell_W'] or data['sigma_U'][i]!=expected['sigma_W']):
                raise ValueError('Factor range/warp parameter ordering mismatch')
        wc,wa=physical_arrays(target,positions)
        if migration_warp_audit is None:
            if not np.array_equal(wc,data['W_cell']) or not np.array_equal(wa,data['W_active']):
                raise ValueError('Physical warp reconstruction mismatch')
        else:
            # All saved arrays and receipts above remain hash-exact. Only the
            # independent recomputation on another processor admits roundoff,
            # bounded by the existing dense-projector absolute tolerance.
            if not isinstance(migration_warp_audit,list):raise ValueError('Migration audit list required')
            error=max(float(np.max(np.abs(wc-data['W_cell']))),float(np.max(np.abs(wa-data['W_active']))))
            if not np.isfinite(error) or error>2e-10:
                raise ValueError('Cross-runtime physical warp error exceeds 2e-10: '+str(error))
            migration_warp_audit.append(dict(sweep=m['sweep'],max_absolute_error=error,tolerance=2e-10))
        projector=target.geometry.arrays['projector'][:,target.geometry.arrays['active_indices']]
        error=max(float(np.max(np.abs(projector@data['W_active'][i]-data['W_cell'][i]))) for i in range(k))
        if error>2e-10: raise ValueError('Independent dense projector mismatch (historical 2e-10)')
        audit=d['sweep_audit']
        if (state_hashes(state)!=audit['state_after'] or [logical_hash(p.values) for p in positions]!=audit['positions_after']
                or logical_hash(compute_Yhat(state.loading,state.eta,slices))!=audit['fitted_Y_sha256']):
            raise ValueError('Retained state/boundary reconstruction mismatch')
    return m,data,d
