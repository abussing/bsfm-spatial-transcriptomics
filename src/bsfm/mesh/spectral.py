import numpy as np
from scipy.linalg import eigh
from .identities import require


def spectrum(mass,stiffness,tol=1e-9):
    m=mass.toarray() if hasattr(mass,'toarray') else np.asarray(mass)
    g=stiffness.toarray() if hasattr(stiffness,'toarray') else np.asarray(stiffness)
    lam,u=eigh(g,m,check_finite=True)
    require(lam.min()>=-tol*max(1,abs(lam).max()),'Materially negative generalized eigenvalue')
    raw=lam.copy();lam=np.maximum(lam,0)  # All n modes retained, including constant mode.
    orth=float(np.max(abs(u.T@m@u-np.eye(len(lam)))))
    residual=float(np.linalg.norm(g@u-(m@u)*lam)/max(np.linalg.norm(g@u),1))
    require(orth<tol and residual<tol,'Generalized eigen invariants')
    return lam,u,dict(modes=len(lam),truncated=False,min_raw_eigenvalue=float(raw.min()),mass_orthogonality=orth,eigen_residual=residual)


def modal(lam,ell):
    require(ell>0 and np.isfinite(ell),'Invalid range')
    k2=40/ell**2;ratio=lam/k2
    w=20*np.pi/k2*np.exp(-6*np.log1p(ratio))
    dw=w*(2-12*ratio/(1+ratio))
    require(np.all(w>0) and np.isfinite(w).all(),'Modal weight underflow/nonfinite; no truncation allowed')
    return w,dw


def full_covariance(u,w):
    return (u*w)@u.T
