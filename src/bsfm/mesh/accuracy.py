import numpy as np
import time
from scipy.spatial.distance import cdist
from .continuum import covariance
from .spectral import modal,full_covariance
from .marginal import active_covariance,root_and_derivative
from .derivatives import check,errors
from .identities import require,logical


def evaluate(u,lam,indices,a,points,probe_indices,probe_metadata,ranges,config):
    p=a[probe_indices]; pa=p[:,indices];xy=points[probe_indices]
    pair_distance=cdist(xy,xy); output=[]
    strata=np.asarray(probe_metadata['strata'])
    for entry in ranges:
        started=time.perf_counter()
        ell=entry['ell'];w,dw=modal(lam,ell)
        full=full_covariance(u,w);active=active_covariance(u,w,indices)
        root_started=time.perf_counter();l,dl,ds=root_and_derivative(u,w,dw,indices);root_seconds=time.perf_counter()-root_started
        equality=errors(active,full[np.ix_(indices,indices)])
        projected=np.asarray(p@full@p.T);projected_active=np.asarray(pa@active@pa.T)
        projected_check=errors(projected_active,projected)
        reconstruction=errors(l@l.T,active)
        derivative=check(u,lam,indices,ell,config['finite_difference_steps'])
        require(max(equality['relative'],projected_check['relative'],reconstruction['relative'])<config['discrete_relative_tolerance'],'Discrete covariance/root invariant')
        require(derivative['identity']['relative']<config['derivative_identity_relative_tolerance'],'Covariance-root derivative identity')
        require(min(x['covariance']['relative'] for x in derivative['finite_differences'])<config['derivative_fd_relative_tolerance'],'Covariance derivative finite difference')
        require(min(x['root']['relative'] for x in derivative['finite_differences'])<config['derivative_fd_relative_tolerance'],'Root derivative finite difference')
        analytic=covariance(xy,ell);variance=np.diag(projected)
        require(np.all(variance>0),'Nonpositive projected variance')
        # Correlation conversion is a diagnostic; the modeled covariance is never rescaled.
        correlation=projected/np.sqrt(variance[:,None]*variance[None,:])
        delta=projected-analytic;corr_error=abs(correlation-analytic)
        def summary(mask):
            return dict(pairs=int(mask.sum()),absolute_covariance=float(np.max(abs(delta[mask]))) if mask.any() else None,
                absolute_correlation=float(np.max(corr_error[mask])) if mask.any() else None,
                relative_covariance_frobenius=float(np.linalg.norm(delta[mask])/max(np.linalg.norm(analytic[mask]),1e-300)) if mask.any() else None)
        bins=[]
        boundaries=[0,.25,.5,1,2,np.inf]
        for lo,hi in zip(boundaries[:-1],boundaries[1:]):
            bins.append(dict(distance_over_range=[lo,hi if np.isfinite(hi) else None],**summary((pair_distance/ell>=lo)&(pair_distance/ell<hi))))
        per_stratum={s:summary((strata==s)[:,None]&(strata==s)[None,:]) for s in np.unique(strata)}
        extra=probe_metadata['gap']['extra_probe_indices'];gap=None
        if extra:
            gp=a[extra];gc=np.asarray(gp@full@gp.T);ref=covariance(points[extra],ell)
            gap=dict(probes=len(extra),variance_error=float(np.max(abs(np.diag(gc)-1))),covariance=errors(gc,ref))
        output.append(dict(range_id=entry['range_id'],ell=ell,role=entry['role'],unit_variance_error=float(np.max(abs(variance-1))),
            **summary(np.ones_like(delta,dtype=bool)),distance_bins=bins,strata=per_stratum,gap=gap,
            full_to_active=equality,projected_full_to_active=projected_check,root_reconstruction=reconstruction,
            derivative=derivative,condition_active=float(np.linalg.cond(active)),
            logical_hashes=dict(full_covariance=logical(full),active_covariance=logical(active),root=logical(l),covariance_derivative=logical(ds),root_derivative=logical(dl),probe_covariance=logical(projected)),
            timing=dict(range_seconds=time.perf_counter()-started,root_and_derivative_seconds=root_seconds),production_accuracy_pass=None))
    return output
