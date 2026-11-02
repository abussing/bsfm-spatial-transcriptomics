import numpy as np
from scipy.linalg import qr, solve_triangular
from .identities import require


def active_covariance(u,w,indices):
    ua=u[indices];return (ua*w)@ua.T


def root_and_derivative(u,w,dw,indices):
    ua=u[indices];b=ua*np.sqrt(w)
    _,r=qr(b.T,mode='economic')
    signs=np.where(np.diag(r)<0,-1.,1.); l=(signs[:,None]*r).T
    require(np.all(np.diag(l)>0),'Rank-deficient active covariance root')
    ds=(ua*dw)@ua.T
    left=solve_triangular(l,ds,lower=True)
    x=solve_triangular(l,left.T,lower=True).T
    phi=np.tril(x);diag=np.diag_indices_from(phi);phi[diag]*=.5
    dl=l@phi
    return l,dl,ds
