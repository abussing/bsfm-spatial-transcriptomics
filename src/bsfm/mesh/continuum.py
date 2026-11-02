import numpy as np
from scipy.special import kve
from scipy.spatial.distance import cdist
from .identities import require


def matern(distance,ell):
    require(np.isfinite(ell) and ell>0,'Positive range required')
    d=np.asarray(distance,dtype=float);require(np.isfinite(d).all() and np.all(d>=0),'Invalid distance')
    z=np.sqrt(40)*d/ell;out=np.ones_like(z)
    tiny=(z>0)&(z<1e-3);u=z[tiny]**2
    # Integer nu=5 series: error O(z^10 log(z)); no cancellation at zero.
    out[tiny]=1-u/16+u*u/384-u**3/9216+u**4/147456
    use=z>=1e-3
    out[use]=np.exp(5*np.log(z[use])+np.log(kve(5,z[use]))-z[use]-np.log(384))
    return out


def covariance(points,ell):
    return matern(cdist(points,points),ell)
