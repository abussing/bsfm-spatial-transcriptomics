"""Versioned pre-sweep endpoint, deliberately not a Layer-7 sweep-zero checkpoint."""
import hashlib
import copy
import numpy as np
from .contracts import GaussianState, logical_hash, array
from .conjugate import compute_Yhat
from .layer4 import STATE_ARRAYS, state_hashes
from .field_target import FieldPosition
from .layer5 import SplitTransition, SplitTuning
from .checkpoint_contract import digest, validate_contract
from .checkpoint_rng import (json_text,parse_json,exact_keys,generator_record,restore_generator,
    global_record,restore_global,key_record,restore_key,stream_audit)
from .retained_records import descriptor
from .retained_diagnostics import decode
from .run_initialization import Endpoint
from .run_storage import write_npz
from .migration_boundary import same_boundary


def boundary(endpoint,target):
    e=endpoint;slices=e.state.validate(target.inputs,factors=len(target.factor_ids))
    return dict(state_after=state_hashes(e.state),positions_after=[logical_hash(p.values) for p in e.positions],
        rng_after=stream_audit(e.eta_rng,e.gauge_rng,e.master_key,e.numpy_global_state),
        fitted_Y_sha256=logical_hash(compute_Yhat(e.state.loading,e.state.eta,slices)),
        target_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),b_sigma2_sha256=logical_hash(e.b_sigma2))


def validate_endpoint(e,target,contract,*,migration_boundary_audit=None):
    validate_contract(contract,target,e.b_sigma2)
    k=len(target.factor_ids)
    if len(e.positions)!=k or len(e.tuning)!=k:raise ValueError('Incomplete genesis tuning/positions')
    split=SplitTransition(target)
    for i,fid in enumerate(target.factor_ids):
        if e.positions[i].factor_id!=fid or e.tuning[i].factor_id!=fid:raise ValueError('Genesis factor order')
        split.validate_inputs(e.master_key,e.positions[i],e.state,e.tuning[i],state_factor_ids=target.factor_ids)
    v=e.evidence
    if v.get('schema')=='bsfm.inherited-endpoint.v1':
        from .run_transactions import tuning_identity
        keys=('schema','initialization','adaptation_steps','source_boundary','source_tuning','source')
        if 'field_step_scales' in v:keys+=('field_step_scales',)
        exact_keys(v,keys)
        expected_tuning=copy.deepcopy(v['source_tuning'])
        if 'field_step_scales' in v:
            from .run import validate_field_step_scales
            validate_field_step_scales(v['field_step_scales'],target.factor_ids)
            if not isinstance(expected_tuning,list) or len(expected_tuning)!=k:
                raise ValueError('Incomplete source tuning')
            for i,row in enumerate(expected_tuning):
                if row['factor_id']!=target.factor_ids[i]:raise ValueError('Source tuning factor order')
                row['step']*=v['field_step_scales'][row['factor_id']]
        exact_keys(v['initialization'],('seed',))
        if (v['adaptation_steps']!=0 or type(v['initialization']['seed']) is not int
                or not same_boundary(boundary(e,target),v['source_boundary'],migration_audit=migration_boundary_audit)
                or expected_tuning!=tuning_identity(e.tuning)
                or v['source'].get('schema')!='bsfm.checkpoint-fork-source.v1'):
            raise ValueError('Inherited endpoint state/RNG/tuning changed')
        return boundary(e,target)
    exact_keys(v,('initialization','adaptation_steps','target_acceptance','factors','rng_before','rng_after'))
    if type(v['adaptation_steps']) is not int or v['adaptation_steps']<20 or v['target_acceptance']!=.9:
        raise ValueError('Incomplete/changed genesis warmup')
    if len(v['factors'])!=k:raise ValueError('Missing warmup histories')
    init = v['initialization']
    start_state = init['state_after'] if init.get('schema') == 'bsfm.readaptation-start.v1' else init['after_PX']
    if (v['factors'][0]['state_before']!=start_state
            or v['rng_before']!=v['initialization']['rng_after']):
        raise ValueError('Initialization/warmup boundary mismatch')
    for i,row in enumerate(v['factors']):
        h=decode(row['history'])
        array(h['state']['position'],'warmup position history',
              (v['adaptation_steps'],len(e.positions[i].values)))
        if (row['factor_id']!=target.factor_ids[i] or row['key']!=v['initialization']['warm_keys'][i]
            or h['state']['position'].shape!=(v['adaptation_steps'],len(e.positions[i].values))
            or not np.array_equal(h['state']['position'][-1],e.positions[i].values)):
            raise ValueError('Warmup endpoint/history mismatch')
        if i and row['state_before']!=v['factors'][i-1]['state_after']:raise ValueError('Warmup state discontinuity')
    if v['factors'][-1]['state_after']!=state_hashes(e.state):raise ValueError('Final warmup state mismatch')
    if v['rng_after']!=boundary(e,target)['rng_after']:raise ValueError('Genesis RNG mismatch')
    for key in ('numpy_global_sha256','gauge_rng_sha256','jax_key_data'):
        if v['rng_before'][key]!=v['rng_after'][key]:raise ValueError('Warmup RNG chronology')
    return boundary(e,target)


def save_genesis(path,e,target,contract):
    b=validate_endpoint(e,target,contract)
    data={n:np.array(getattr(e.state,n),copy=True,order='K') for n in STATE_ARRAYS}
    kr,kd=key_record(e.master_key)
    data.update(positions=np.stack([p.values for p in e.positions]),b_sigma2=e.b_sigma2.copy(),
        field_steps=np.array([t.step_size for t in e.tuning]),hyper_steps=np.array([t.hyper_step_size for t in e.tuning]),
        inverse_mass=np.stack([t.inverse_mass_matrix for t in e.tuning]),master_key=kd,
        numpy_global_keys=e.numpy_global_state[1].copy())
    data.update({'spectral_'+k:np.array(v,copy=True,order='K') for k,v in target.geometry.spectral.items() if k!='audit'})
    schema='bsfm.inherited-endpoint.v1' if e.evidence.get('schema')=='bsfm.inherited-endpoint.v1' else 'bsfm.pre-sweep-endpoint.v1'
    m=dict(schema=schema,contract=contract.json,contract_sha256=contract.sha256,
        factor_ids=list(target.factor_ids),boundary=b,evidence=e.evidence,
        rng=dict(eta=generator_record(e.eta_rng),gauge=generator_record(e.gauge_rng),
                 numpy_global=global_record(e.numpy_global_state),jax=kr),
        spectral_audit=target.geometry.spectral['audit'],arrays={n:descriptor(a) for n,a in data.items()})
    m['logical_sha256']=digest(m);data['metadata']=np.array(json_text(m));write_npz(path,data)
    return load_genesis(path,target,contract)


def load_genesis(path,target,contract,*,migration_boundary_audit=None):
    with np.load(path,allow_pickle=False) as z:
        if len(z.files)!=len(set(z.files)):raise ValueError('Duplicate genesis member')
        d={n:z[n].copy(order='K') for n in z.files}
    raw=d.pop('metadata')
    if raw.shape!=() or raw.dtype.kind!='U':raise ValueError('Genesis metadata')
    m=parse_json(str(raw));exact_keys(m,('schema','contract','contract_sha256','factor_ids','boundary','evidence','rng','spectral_audit','arrays','logical_sha256'))
    if m['schema'] not in ('bsfm.pre-sweep-endpoint.v1','bsfm.inherited-endpoint.v1') or m['logical_sha256']!=digest({k:v for k,v in m.items() if k!='logical_sha256'}):raise ValueError('Genesis identity')
    if (m['schema']=='bsfm.inherited-endpoint.v1') != (m['evidence'].get('schema')=='bsfm.inherited-endpoint.v1'):
        raise ValueError('Endpoint evidence/schema mismatch')
    expected=set(STATE_ARRAYS)|{'positions','b_sigma2','field_steps','hyper_steps','inverse_mass','master_key','numpy_global_keys'}|{'spectral_'+k for k in target.geometry.spectral if k!='audit'}
    if set(d)!=expected or set(m['arrays'])!=expected:raise ValueError('Missing/extra genesis fields')
    if m['contract']!=contract.json or m['contract_sha256']!=contract.sha256 or m['factor_ids']!=list(target.factor_ids):raise ValueError('Genesis contract/factor mismatch')
    for n,a in d.items():
        if descriptor(a)!=m['arrays'][n]:raise ValueError('Genesis array hash mismatch')
    if m['spectral_audit']!=target.geometry.spectral['audit']:raise ValueError('Spectral audit changed')
    for key,v in target.geometry.spectral.items():
        if key=='audit':continue
        a=d['spectral_'+key];v=np.asarray(v)
        if a.dtype!=v.dtype or a.shape!=v.shape or not np.array_equal(a,v):raise ValueError('Exact spectral chart mismatch')
    state=GaussianState(**{n:d[n] for n in STATE_ARRAYS},input_identity_json=target.inputs.identity_json)
    k=len(target.factor_ids);dimension=target.position_dimension
    array(d['positions'],'genesis positions',(k,dimension))
    array(d['field_steps'],'genesis field steps',(k,),positive=True)
    array(d['hyper_steps'],'genesis hyper steps',(k,),positive=True)
    array(d['inverse_mass'],'genesis inverse mass',(k,dimension),positive=True)
    positions=[];tuning=[]
    for i,fid in enumerate(target.factor_ids):
        p=d['positions'][i].copy();mass=d['inverse_mass'][i].copy();p.flags.writeable=mass.flags.writeable=False
        positions.append(FieldPosition(p,fid,target.identity))
        tuning.append(SplitTuning(target.identity,fid,float(d['field_steps'][i]),float(d['hyper_steps'][i]),mass,logical_hash(mass)))
    exact_keys(m['rng'],('eta','gauge','numpy_global','jax'))
    e=Endpoint(state,tuple(positions),tuple(tuning),restore_generator(m['rng']['eta']),restore_generator(m['rng']['gauge']),
        restore_key(m['rng']['jax'],d['master_key']),restore_global(m['rng']['numpy_global'],d['numpy_global_keys']),d['b_sigma2'],m['evidence'])
    if not same_boundary(validate_endpoint(e,target,contract,migration_boundary_audit=migration_boundary_audit),
                         m['boundary'],migration_audit=migration_boundary_audit):
        raise ValueError('Genesis boundary changed')
    return e,m['logical_sha256']
