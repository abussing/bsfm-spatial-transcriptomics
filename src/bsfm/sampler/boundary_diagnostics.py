"""Detached Gibbs-boundary evidence and fixed-chart diagnostic algebra.

No adaptation or production sampling. Roots map two independent whitened
columns to the physical direct warp; no reference-coordinate offset is added.
"""
from dataclasses import asdict, is_dataclass
import hashlib
import json
from pathlib import Path
import numpy as np
import jax.numpy as jnp
from .contracts import logical_hash
from .layer4 import state_hashes


def fixed_chart_field(value_grad, position, prior_root, chart_root):
    """Pull a fixed-hyperparameter field target back to W=chart_root @ r.

    value_grad accepts the original complete position, with its conditional
    statistics already closed over. prior_root is the whitening root for that
    position's hyperparameters. Both roots stay constant along the probe.
    The density includes the two-column change-of-variables determinant.
    """
    prior_root=np.asarray(prior_root);chart_root=np.asarray(chart_root)
    if prior_root.shape != chart_root.shape or prior_root.ndim != 2 or prior_root.shape[0] != prior_root.shape[1]:
        raise ValueError('Matching square roots required')
    if len(position) != 4+2*len(prior_root):
        raise ValueError('Expected two direct-warp columns')
    signs,logs=zip(*(np.linalg.slogdet(b) for b in (prior_root,chart_root)))
    if any(s <= 0 for s in signs) or not np.isfinite(logs).all():
        raise ValueError('Finite positive root determinants required')
    transform=jnp.asarray(np.linalg.solve(prior_root,chart_root))
    logjac=2*(logs[1]-logs[0])
    q=jnp.asarray(position)
    def evaluate(x):
        z=transform @ x[2:].reshape(-1,2)
        p=q.at[:2].set(x[:2]).at[4:].set(z.reshape(-1))
        value,gradient=value_grad(p)
        field_gradient=jnp.concatenate((gradient[:2],
            (transform.T @ gradient[4:].reshape(-1,2)).reshape(-1)))
        return value+logjac,field_gradient
    physical=prior_root @ np.asarray(position[4:]).reshape(-1,2)
    x=np.r_[np.asarray(position[:2]),np.linalg.solve(chart_root,physical).reshape(-1)]
    return evaluate,x


def feature_covariance_distance(first,second,*,nugget_first=0.,nugget_second=0.):
    """Exact Frobenius distance of AA' + vI using only feature-size Gram matrices.

    Columns already include spatial standard deviation. Cells must have identical
    order. This is model-covariance movement, not parameter displacement.
    """
    a=np.asarray(first);b=np.asarray(second)
    if a.ndim!=2 or b.ndim!=2 or a.shape[0]!=b.shape[0]:
        raise ValueError('Matching ordered cells required')
    if not np.isfinite(a).all() or not np.isfinite(b).all() or not np.isfinite([nugget_first,nugget_second]).all() or min(nugget_first,nugget_second)<0:
        raise ValueError('Finite features and nonnegative nugget variances required')
    aa=a.T@a;bb=b.T@b;ab=a.T@b
    delta=nugget_second-nugget_first
    squared=np.sum(aa*aa)+np.sum(bb*bb)-2*np.sum(ab*ab)
    squared+=2*delta*(np.sum(b*b)-np.sum(a*a))+len(a)*delta*delta
    norm2=np.sum(aa*aa)+2*nugget_first*np.sum(a*a)+len(a)*nugget_first**2
    distance=float(np.sqrt(max(0.,squared)))
    return dict(frobenius=distance,relative_to_first=distance/np.sqrt(norm2) if norm2>0 else None)


def _json(value):
    if is_dataclass(value):return asdict(value)
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,np.ndarray):return value.tolist()
    raise TypeError(type(value).__name__)


class BoundaryRecorder:
    """Save only selected-factor sufficient statistics, not duplicate full states.

    Output is provisional until the enclosing transition replay authenticates it.
    Snapshots include hashes of every Gibbs state array to identify the changes.
    """
    def __init__(self,target,factor_index,tuning,directory):
        self.target=target;self.index=factor_index;self.tuning=tuning
        self.directory=Path(directory)
        self.directory.mkdir(exist_ok=False)
        self.rows=[]

    def conditional(self,event,position,u,ct,penalty,**metadata):
        arrays=dict(position=np.asarray(position),u=np.asarray(u),ct=np.asarray(ct),
                    penalty=np.asarray(penalty),inverse_mass=self.tuning.inverse_mass_matrix,
                    step=np.asarray(self.tuning.step_size),
                    hyper_step=np.asarray(self.tuning.hyper_step_size))
        filename=f'{len(self.rows):03d}-{event}.npz'
        path=self.directory/filename
        np.savez_compressed(path,**arrays)
        row=dict(event=event,file=filename,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                 array_hashes={k:logical_hash(v) for k,v in arrays.items()},**metadata)
        self.rows.append(row)
        self.publish(authenticated=False)

    def __call__(self,event,state,positions,details):
        u,ct,penalty,context=self.target.context(state,
            factor_id=self.target.factor_ids[self.index],state_factor_ids=self.target.factor_ids)
        self.conditional(event,positions[self.index].values,u,ct,penalty,
                         details=details,state_hashes=state_hashes(state),context=context)

    def publish(self,*,authenticated):
        (self.directory/'index.json').write_text(json.dumps(dict(
            schema='bsfm.gibbs-boundary-capture.v1',
            authenticated_transition_replay=authenticated,
            factor_id=self.target.factor_ids[self.index],rows=self.rows),
            indent=2,default=_json,allow_nan=False)+'\n')
