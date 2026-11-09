"""Authenticated current-state direct-W factor target; no Markov transitions.

Every value/gradient/draw call reconstructs statistics from the supplied state.
Only fixed geometry/rule kernels are cached, never a Gibbs-state density/context.
"""
from dataclasses import dataclass
import hashlib
import json
import jax
import jax.numpy as jnp
import numpy as np
from scipy.special import expit
from .contracts import array, logical_hash, MU_LOG_ALPHA, VAR_LOG_ALPHA
from .conjugate import compute_Yhat
from .factor_statistics import factor_context, sample_single_eta
from .field_kernels import build_direct_target
from .projector_encoding import barycentric_triplets


def kernel_arguments(inputs, geometry, rule):
    idx=geometry.arrays['active_indices']
    indices,weights,_=barycentric_triplets(geometry.arrays['projector'][:,idx])
    return dict(slocs=inputs.arrays['slocs'],cell_vertex_idx=indices,cell_weights=weights,
                u_active=geometry.spectral['U'][idx],spectral=geometry.spectral,
                omega=rule.arrays['omega'],sqrt_weights=rule.arrays['sqrt_weights'],
                mu_log_alpha=MU_LOG_ALPHA,variance_log_alpha=VAR_LOG_ALPHA,
                a_zeta=2.,b_zeta=2.,loading_dimension=len(inputs.arrays['gene_names'])*len(inputs.arrays['cell_type_names']),
                ell_eta_reference=.14,mu_log_ell_u=0.,variance_log_ell_u=.5**2,
                mu_log_sigma_u=-.5*np.log(10.),variance_log_sigma_u=.5**2,
                variance_log_r_W=.3**2)


@dataclass(frozen=True)
class FieldPosition:
    values: np.ndarray
    factor_id: str
    target_identity: str


class DirectWTarget:
    @property
    def position_dimension(self):
        return 4 + 2*len(self.geometry.arrays['active_indices'])

    @property
    def range_contract(self):
        return .14

    def hyperparameters(self, position):
        self._check_position(position)
        p = position.values
        return dict(ell_eta=.14, ell_W=float(np.exp(np.asarray(p[2]))),
                    sigma_W=float(np.exp(np.asarray(
                        jnp.asarray(p[3])+(jnp.asarray(p[2])-.5*np.log(10.))))))

    def __init__(self, inputs, geometry, rule, *, factor_ids):
        self.inputs,self.geometry,self.rule=inputs,geometry,rule
        if (not isinstance(factor_ids,tuple) or not factor_ids
                or any(not isinstance(x,str) or not x for x in factor_ids)
                or len(set(factor_ids))!=len(factor_ids)):
            raise ValueError('Explicit unique ordered factor IDs required')
        self.factor_ids=factor_ids
        self._validate_identities()
        self.identity=json.dumps(dict(schema='bsfm.direct-W-factor-target.v1',
            input=json.loads(inputs.identity_json),warp=json.loads(geometry.identity_json),
            rule=json.loads(rule.identity_json),factor_ids=list(factor_ids),
            position_order=['log_alpha','logit_zeta','log_ell_W','log_r_W','zW_row_major_two_columns'],
            priors=dict(log_alpha_mean=MU_LOG_ALPHA,log_alpha_variance=VAR_LOG_ALPHA,
                        zeta_beta=[2.,2.],log_ell_mean=0.,log_ell_variance=.25,log_r_mean=0.,log_r_variance=.3**2)),sort_keys=True)
        self._kernels=build_direct_target(**kernel_arguments(inputs,geometry,rule))

    def _validate_identities(self):
        self.inputs.validate();self.geometry.validate();self.rule.validate()
        a=json.loads(self.inputs.identity_json);b=json.loads(self.geometry.identity_json)
        if (a['section']!=b['section'] or a['coordinate_system']!='october26_glial_min_max_span'
                or a['coordinate_system']!=b['coordinate_system'] or a['axis_order']!=b['axis_order']):
            raise ValueError('Section/coordinate chart mismatch; no implicit normalization')
        for left,right in [('slocs','locations'),('cell_names','cell_ids'),('source_row_indices','source_rows')]:
            if not np.array_equal(self.inputs.arrays[left],self.geometry.arrays[right]):
                raise ValueError('Input/warp cell identity or ordering mismatch: '+left)
        if hasattr(self,'identity'):
            expected=json.loads(self.identity)
            if (a!=expected['input'] or b!=expected['warp']
                    or json.loads(self.rule.identity_json)!=expected['rule']
                    or list(self.factor_ids)!=expected['factor_ids']):
                raise ValueError('Fixed target binding replaced; rebuild the target explicitly')
        if not jax.config.x64_enabled:raise ValueError('JAX x64 required')

    def position(self, factor_id, *, log_alpha, logit_zeta, log_ell, log_r, zW):
        n=len(self.geometry.arrays['active_indices']);array(zW,'zW',(n,2))
        scalars=(log_alpha,logit_zeta,log_ell,log_r)
        if any(np.ndim(x)!=0 or isinstance(x,(bool,np.bool_)) or not np.isfinite(x) for x in scalars):
            raise ValueError('Four finite scalar chart coordinates required')
        values=np.r_[np.asarray(scalars,np.float64),zW.reshape(-1)]
        result=FieldPosition(values,factor_id,self.identity);self._check_position(result)
        values.flags.writeable=False
        return result

    def _check_position(self, position):
        if not isinstance(position,FieldPosition) or position.target_identity!=self.identity:
            raise ValueError('Position target identity mismatch')
        if position.factor_id not in self.factor_ids:raise ValueError('Unknown factor identity')
        array(position.values,'position',(4+2*len(self.geometry.arrays['active_indices']),))
        x=position.values
        with np.errstate(over='ignore',under='ignore'):
            alpha2=np.exp(2*x[0]);ell=np.exp(x[2]);r=np.exp(x[3]);sigma=np.exp(x[2]+x[3]-.5*np.log(10.))
        zeta=expit(x[1])
        if not all(np.isfinite(v) and v>0 for v in (alpha2,ell,r,sigma)) or not 0<zeta<1:
            raise ValueError('Nonrepresentable alpha/zeta/warp parameters; no clipping')

    def context(self,state,*,factor_id,state_factor_ids):
        self._validate_identities()
        if state_factor_ids!=self.factor_ids or factor_id not in self.factor_ids:
            raise ValueError('Ordered state/factor identities do not match target')
        slices=state.validate(self.inputs,factors=len(self.factor_ids));k=self.factor_ids.index(factor_id)
        y=self.inputs.arrays['Y']
        # Recompute from the supplied current state; never accept a cached Yhat.
        yhat=compute_Yhat(state.loading,state.eta,slices)
        u,ct,penalty=factor_context(y,yhat,state.loading,state.eta,state.sigma2,state.phi,
                                  state.tau,np.full(len(self.factor_ids),.2),k,self.inputs.arrays['cell_id'])
        array(u,'u',(y.shape[1],),nonnegative=True);array(ct,'ct',u.shape)
        if not np.isfinite(penalty) or penalty<0:raise ValueError('Invalid loading penalty')
        hashes={name:logical_hash(getattr(state,name)) for name in ('loading','eta','alpha','zeta','sigma2','phi','delta','tau')}
        identity=dict(target_sha256=hashlib.sha256(self.identity.encode()).hexdigest(),factor_id=factor_id,
                      state_array_hashes=hashes,u_sha256=logical_hash(u),ct_sha256=logical_hash(ct),penalty=penalty)
        return u,ct,penalty,identity

    def value_grad(self,position,state,*,state_factor_ids):
        self._check_position(position)
        u,ct,penalty,identity=self.context(state,factor_id=position.factor_id,state_factor_ids=state_factor_ids)
        value,gradient=self._kernels['value_grad'](jnp.asarray(position.values),jnp.asarray(u),jnp.asarray(ct),jnp.asarray(penalty))
        if not np.isfinite(value) or not np.isfinite(gradient).all():raise RuntimeError('Nonfinite factor target')
        return float(value),np.asarray(gradient),identity

    def features(self,position):
        self._validate_identities();self._check_position(position)
        w,wa,phi=self._kernels['warp_features'](jnp.asarray(position.values))
        if not all(np.isfinite(v).all() for v in (w,wa,phi)):raise RuntimeError('Nonfinite factor features')
        return np.asarray(w),np.asarray(wa),np.asarray(phi)

    def draw_eta(self,position,state,rng,*,state_factor_ids):
        if not isinstance(rng,np.random.Generator):raise ValueError('Explicit NumPy Generator required')
        self._check_position(position)
        u,ct,penalty,identity=self.context(state,factor_id=position.factor_id,state_factor_ids=state_factor_ids)
        phi=self.features(position)[2]
        result=sample_single_eta(rng,features=phi,alpha=np.exp(position.values[0]),
                                 zeta=float(jax.nn.sigmoid(jnp.asarray(position.values[1]))),u=u,ct=ct)
        array(result,'eta draw',u.shape)
        return result,identity
