"""Independent low-dimensional importance integration for fixed-target diagnostics."""
import numpy as np


def conditional_reference(vg, starts, *, seed, power):
    """Two scrambled Sobol replicates of full-support multivariate-t integration.

    This is a numerical reference with recorded overlap/error diagnostics, not
    an exact posterior oracle or a proof that all modes have been located.
    """
    from scipy.optimize import minimize
    from scipy.special import logsumexp
    from scipy.stats import qmc, norm, chi2, multivariate_t
    if not 6 <= power <= 14:
        raise ValueError("Bounded reference size required")
    fits=[]
    def objective(q):
        value,gradient=vg(q)
        return -float(value),-np.asarray(gradient,float)
    for start in starts:
        fit=minimize(objective,np.asarray(start,float),jac=True,method="BFGS",
                     options=dict(gtol=1e-5,maxiter=150))
        fits.append(dict(position=fit.x.tolist(),negative_logdensity=float(fit.fun),
                         gradient_norm=float(np.linalg.norm(fit.jac)),
                         optimizer_success=bool(fit.success),message=str(fit.message)))
    best=min(fits,key=lambda f:f["negative_logdensity"])
    mode=np.array(best["position"])
    if not np.isfinite(best["negative_logdensity"]) or best["gradient_norm"]>0.1:
        raise RuntimeError("No sufficiently stationary finite reference center")
    columns=[]
    for e in np.eye(len(mode))*1e-4:
        columns.append(-(np.asarray(vg(mode+e)[1])-np.asarray(vg(mode-e)[1]))/(2e-4))
    H=np.column_stack(columns);H=(H+H.T)/2
    ev=np.linalg.eigvalsh(H)
    if ev.min()<=0:
        raise RuntimeError("Nonpositive reference-center Hessian")
    covariance=np.linalg.inv(H)
    # Include all found centers; scales 1 and 3, full-support t5 tails.
    centers=[]
    for fit in fits:
        point=np.array(fit["position"])
        if np.isfinite(fit["negative_logdensity"]) and fit["gradient_norm"]<.1:
            if not any(np.linalg.norm(point-c)<1e-3 for c in centers):
                centers.append(point)
    components=[(c,covariance*scale**2) for c in centers for scale in [1.,3.]]
    rows=[];allpoints=[];allweights=[]
    for replicate in range(2):
        u=qmc.Sobol(d=len(mode)+2,scramble=True,seed=seed+replicate).random_base2(power)
        u=np.clip(u,np.finfo(float).eps,1-np.finfo(float).eps)
        component=np.minimum((u[:,0]*len(components)).astype(int),len(components)-1)
        z=norm.ppf(u[:,1:-1])/np.sqrt(chi2.ppf(u[:,-1],5)/5)[:,None]
        points=np.empty_like(z)
        for j,(center,cov) in enumerate(components):
            selected=component==j
            points[selected]=center+z[selected]@np.linalg.cholesky(cov).T
        logproposal=logsumexp(np.array([multivariate_t.logpdf(points,loc=c,shape=cov,df=5)
                                      for c,cov in components]),axis=0)-np.log(len(components))
        logtarget=np.array([float(vg(point)[0]) for point in points])
        if np.isnan(logtarget).any() or np.isposinf(logtarget).any():
            raise FloatingPointError("Invalid reference log density")
        logweight=logtarget-logproposal
        logsum=logsumexp(logweight);weights=np.exp(logweight-logsum)
        mean=weights@points
        centered=points-mean
        cov=centered.T@(weights[:,None]*centered)
        rows.append(dict(log_normalizer=float(logsum-np.log(len(points))),
                         weight_ess=float(1/np.sum(weights**2)),
                         maximum_weight=float(weights.max()),mean=mean.tolist(),
                         covariance=cov.tolist(),finite_fraction=float(np.isfinite(logtarget).mean())))
        allpoints.append(points);allweights.append(logweight)
    logweights=np.concatenate(allweights)
    normalized=np.exp(logweights-logsumexp(logweights))
    points=np.concatenate(allpoints)
    summary=dict(optimizers=fits,hessian=H.tolist(),hessian_eigenvalues=ev.tolist(),
                 components=len(components),replicates=rows,power=power,
                 meaning="Independent integration estimate; check replicate agreement and weight concentration")
    return summary,points,normalized

