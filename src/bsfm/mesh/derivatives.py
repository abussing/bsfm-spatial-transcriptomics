import numpy as np
from .spectral import modal
from .marginal import active_covariance,root_and_derivative


def errors(a,b):
    return dict(absolute=float(np.max(abs(a-b))),relative=float(np.linalg.norm(a-b)/max(np.linalg.norm(b),np.finfo(float).tiny)))


def check(u,lam,indices,ell,steps=(1e-3,1e-4,1e-5)):
    w,dw=modal(lam,ell);l,dl,ds=root_and_derivative(u,w,dw,indices)
    rows=[]
    for step in steps:
        wp,dwp=modal(lam,ell*np.exp(step));wm,dwm=modal(lam,ell*np.exp(-step))
        sp=active_covariance(u,wp,indices);sm=active_covariance(u,wm,indices)
        lp=root_and_derivative(u,wp,dwp,indices)[0];lm=root_and_derivative(u,wm,dwm,indices)[0]
        rows.append(dict(step=step,covariance=errors((sp-sm)/(2*step),ds),root=errors((lp-lm)/(2*step),dl)))
    return dict(identity=errors(dl@l.T+l@dl.T,ds),finite_differences=rows)
