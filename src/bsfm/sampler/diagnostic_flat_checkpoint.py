"""Diagnostic flat endpoints; not production posterior records."""
import json
import os
import tempfile
from pathlib import Path
import numpy as np
from .checkpoint_contract import digest
from .checkpoint_rng import (generator_record, restore_generator, global_record,
    restore_global, key_record, restore_key, json_text)
from .contracts import GaussianState
from .field_target import FieldPosition
from .layer4 import STATE_ARRAYS
from .retained_records import descriptor
from .run_initialization import Endpoint


def save_endpoint(path, endpoint, target, transition, *, method, plan_hash, sweep, epoch):
    """Atomically replace only the last complete diagnostic boundary."""
    path=Path(path)
    e=endpoint
    arrays={n:np.array(getattr(e.state,n),copy=True) for n in STATE_ARRAYS}
    kr,kd=key_record(e.master_key)
    arrays.update(positions=np.stack([p.values for p in e.positions]),
        steps=np.array([t.step_size for t in e.tuning]),
        masses=np.stack([t.inverse_mass_matrix for t in e.tuning]),
        b_sigma2=e.b_sigma2.copy(),master_key=kd,
        global_keys=e.numpy_global_state[1].copy())
    metadata=dict(schema="bsfm.diagnostic-flat-endpoint.v1",method=method,
        plan_hash=plan_hash,sweep=sweep,epoch=epoch,target=target.identity,
        factor_ids=list(target.factor_ids),
        rng=dict(eta=generator_record(e.eta_rng),gauge=generator_record(e.gauge_rng),
            numpy=global_record(e.numpy_global_state),jax=kr),
        arrays={n:descriptor(a) for n,a in arrays.items()})
    metadata["logical_sha256"]=digest(metadata)
    arrays["metadata"]=np.array(json_text(metadata))
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix=".endpoint-",suffix=".npz",dir=path.parent)
    try:
        with os.fdopen(fd,"wb") as out:
            np.savez(out,**arrays);out.flush();os.fsync(out.fileno())
        # Decode before publishing; this also checks state, tuning and RNG.
        load_endpoint(temp,target,transition,method=method,plan_hash=plan_hash)
        os.replace(temp,path)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return metadata["logical_sha256"]


def load_endpoint(path,target,transition,*,method,plan_hash):
    with np.load(path,allow_pickle=False) as z:
        arrays={n:z[n].copy() for n in z.files}
    metadata=json.loads(str(arrays.pop("metadata")))
    expected_hash=metadata.pop("logical_sha256")
    if digest(metadata)!=expected_hash:
        raise ValueError("Diagnostic endpoint metadata hash")
    if (metadata["schema"]!="bsfm.diagnostic-flat-endpoint.v1"
        or metadata["method"]!=method or metadata["plan_hash"]!=plan_hash
        or metadata["target"]!=target.identity
        or metadata["factor_ids"]!=list(target.factor_ids)):
        raise ValueError("Diagnostic endpoint identity")
    if {n:descriptor(a) for n,a in arrays.items()}!=metadata["arrays"]:
        raise ValueError("Diagnostic endpoint array hash")
    state=GaussianState(**{n:arrays[n] for n in STATE_ARRAYS},
                        input_identity_json=target.inputs.identity_json)
    state.validate(target.inputs,factors=len(target.factor_ids))
    positions=[];tunings=[]
    for i,fid in enumerate(target.factor_ids):
        p=FieldPosition(arrays["positions"][i],fid,target.identity)
        target._check_position(p)
        t=transition.tuning(fid,step_size=float(arrays["steps"][i]),hyper_step_size=1.,
                            inverse_mass_matrix=arrays["masses"][i])
        positions.append(p);tunings.append(t)
    r=metadata["rng"]
    ep=Endpoint(state,tuple(positions),tuple(tunings),
        restore_generator(r["eta"]),restore_generator(r["gauge"]),
        restore_key(r["jax"],arrays["master_key"]),
        restore_global(r["numpy"],arrays["global_keys"]),arrays["b_sigma2"],
        dict(diagnostic_only=True,sweep=metadata["sweep"],epoch=metadata["epoch"]))
    for p,t in zip(ep.positions,ep.tuning):
        transition.validate_inputs(ep.master_key,p,ep.state,t,
                                   state_factor_ids=target.factor_ids)
    return ep,metadata

