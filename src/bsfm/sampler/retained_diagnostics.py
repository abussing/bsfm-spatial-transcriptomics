"""Lossless mechanical diagnostics and raw summaries, without convergence gates."""
import base64
from dataclasses import asdict, is_dataclass
import hashlib
import numpy as np
from .checkpoint_rng import exact_keys, json_text
from .joint_eta_kernels import JointEtaDiagnostics
from .split_kernels import Info


def encode(value):
    if is_dataclass(value):
        return encode(asdict(value))
    if hasattr(value, '_asdict'):
        return encode(value._asdict())
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError('String diagnostic keys required')
        return {k: encode(v) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encode(v) for v in value]
    if hasattr(value, 'dtype'):
        a = np.asarray(value)
        if a.dtype.kind not in 'biuf' or a.dtype.itemsize not in (1,4,8):
            raise ValueError('Unsupported diagnostic array dtype')
        b = a.tobytes(order='C')
        return dict(_array=True, dtype=a.dtype.str, shape=list(a.shape),
                    data=base64.b64encode(b).decode('ascii'), sha256=hashlib.sha256(b).hexdigest())
    if isinstance(value, float) and not np.isfinite(value):
        return dict(_nonfinite=str(value))
    if value is None or type(value) in (str, bool, int, float):
        return value
    raise ValueError('Unsupported diagnostic value')


def decode(value):
    if isinstance(value, list):
        return [decode(v) for v in value]
    if isinstance(value, dict):
        if '_array' in value:
            exact_keys(value, ('_array','dtype','shape','data','sha256'))
            dtype = np.dtype(value['dtype'])
            shape = value['shape']
            if (value['_array'] is not True or dtype.kind not in 'biuf'
                    or dtype.itemsize not in (1,4,8) or not isinstance(shape,list)
                    or any(type(v) is not int or v < 0 for v in shape)):
                raise ValueError('Malformed diagnostic array')
            b = base64.b64decode(value['data'], validate=True)
            if hashlib.sha256(b).hexdigest() != value['sha256']:
                raise ValueError('Diagnostic array hash mismatch')
            a = np.frombuffer(b, dtype=dtype).reshape(shape).copy()
            if encode(a) != value:
                raise ValueError('Noncanonical diagnostic array')
            return a
        if '_nonfinite' in value:
            exact_keys(value, ('_nonfinite',))
            if value['_nonfinite'] not in ('nan','inf','-inf'):
                raise ValueError('Invalid nonfinite tag')
            return float(value['_nonfinite'])
        return {k:decode(v) for k,v in value.items()}
    return value


def event_records(events):
    if not isinstance(events, list):
        raise ValueError('Explicit event list required, including []')
    for e in events:
        exact_keys(e, ('severity','code','message'))
        if e['severity'] not in ('warning','failure') or any(
                not isinstance(e[k],str) or not e[k] for k in ('code','message')):
            raise ValueError('Invalid warning/failure event')
    return events


def diagnostics_for(result, *, events, elapsed_seconds):
    event_records(events)
    if elapsed_seconds is not None and (type(elapsed_seconds) not in (float,int)
            or not np.isfinite(elapsed_seconds) or elapsed_seconds < 0):
        raise ValueError('Caller-measured sweep duration must be finite and nonnegative')
    d = dict(factor_order=list(result.factor_order), pcg=result.pcg_diagnostics,
             px=result.px_audit, warp=result.warp_summaries,
             factors=[dict(factor_index=r['factor_index'], factor_id=r['factor_id'],
                 info=r['transition'].info, transition_audit=r['transition'].audit,
                 eta_audit=r['eta_audit']) for r in result.factor_diagnostics],
             sweep_audit=result.audit, events=events, elapsed_seconds=elapsed_seconds,
             timing_semantics='caller_monotonic_complete_sweep_excluding_archive_io',
             fidelity_status='not_evaluated_by_layers_1_to_8')
    return encode(d)


def validate_diagnostics(encoded, factor_ids, *, failed=False):
    d = decode(encoded)
    if failed:
        exact_keys(d, ('events','last_completed_sweep','attempted_sweep','partial_diagnostics'))
        event_records(d['events'])
        if not any(e['severity']=='failure' for e in d['events']):
            raise ValueError('Failure record must preserve a failure event')
        # Explicitly partial, never interpreted as a completed transition.
        json_text(encoded)
        return d
    exact_keys(d, ('factor_order','pcg','px','warp','factors','sweep_audit','events',
                   'elapsed_seconds','timing_semantics','fidelity_status'))
    k = len(factor_ids)
    if sorted(d['factor_order']) != list(range(k)) or any(type(i) is not int for i in d['factor_order']):
        raise ValueError('Invalid visitation order')
    if len(d['pcg']) != 3 or len(d['factors']) != k or len(d['warp']) != k:
        raise ValueError('Incomplete sweep diagnostics')
    for row in d['pcg']:
        exact_keys(row, JointEtaDiagnostics.__dataclass_fields__)
        if (row['converged'] is not True or row['requested_posterior_mahalanobis_RMS_tolerance'] != 1e-10
                or type(row['iterations']) is not int or not 0 <= row['iterations'] <= 4096
                or not 0 <= row['posterior_mahalanobis_RMS_error_upper_bound'] <= 1e-10
                or not all(np.isfinite(v) for v in row.values())):
            raise ValueError('Invalid completed PCG result; record failure separately')
    exact_keys(d['px'], ('label','old_alpha','new_alpha','checks_relative',
                         'exact_prior_draw','identified_state_preserved'))
    exact_keys(d['px']['checks_relative'], ('identified_loading','standardized_factor','signal','alpha2_q'))
    if (d['px']['exact_prior_draw'] is not True or d['px']['identified_state_preserved'] is not True
            or any(not np.isfinite(v) or not 0 <= v <= 5e-13 for v in d['px']['checks_relative'].values())):
        raise ValueError('Invalid completed PX invariant')
    for j,row in enumerate(d['factors']):
        exact_keys(row, ('factor_index','factor_id','info','transition_audit','eta_audit'))
        i = d['factor_order'][j]
        if row['factor_index'] != i or row['factor_id'] != factor_ids[i]:
            raise ValueError('Factor visitation/binding mismatch')
        info = row['info']; exact_keys(info, Info._fields)
        for n in ('block_acceptance','block_divergent','block_leapfrogs','block_energy'):
            if np.asarray(info[n]).shape != (2,):
                raise ValueError('Two split-block diagnostics required')
        ac = np.asarray(info['block_acceptance']); dv = np.asarray(info['block_divergent'])
        if (not np.isfinite(ac).all() or np.any((ac<0)|(ac>1)) or dv.dtype.kind != 'b'
                or bool(info['is_divergent']) != bool(dv.any())
                or np.any(~np.isfinite(info['block_energy']) & ~dv)
                or not np.isfinite(info['hyper_W_relative_error'])
                or float(info['hyper_W_relative_error']) >= 2e-8):
            raise ValueError('Invalid split diagnostics')
    event_records(d['events'])
    if any(e['severity']=='failure' for e in d['events']):
        raise ValueError('Failure cannot be stored as a completed sweep')
    if d['timing_semantics'] != 'caller_monotonic_complete_sweep_excluding_archive_io' or d['fidelity_status'] != 'not_evaluated_by_layers_1_to_8':
        raise ValueError('Unknown diagnostic semantics')
    elapsed = d['elapsed_seconds']
    if elapsed is not None and (type(elapsed) not in (int,float) or not np.isfinite(elapsed) or elapsed < 0):
        raise ValueError('Invalid timing')
    return d
