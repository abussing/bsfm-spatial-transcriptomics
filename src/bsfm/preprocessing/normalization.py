"""Explicit library scaling and training-population centering for new datasets.

Not a replacement for the accepted SCT recipe. Already transformed inputs must
carry their original transformation provenance and must not enter log_library_size.
"""
import math
import numpy as np


def log_library_size(counts, *, target_sum, log_base):
    """Scale genes-by-cells raw integer counts to an explicit library target.

    Caller supplies the full measured gene universe before modeling selection.
    For predictive work the target must be fixed independently or from training
    cells, not estimated inside this function from all observations.
    """
    x=np.asarray(counts,dtype=np.float64)
    if x.ndim!=2 or min(x.shape)==0 or not np.isfinite(x).all() or np.any(x<0) or np.any(x!=np.floor(x)):
        raise ValueError('Finite nonnegative raw integer counts required')
    if not math.isfinite(target_sum) or target_sum<=0:
        raise ValueError('Explicit positive target_sum required')
    if not math.isfinite(log_base) or log_base<=1:
        raise ValueError('Explicit logarithm base >1 required')
    totals=x.sum(axis=0)
    if not np.isfinite(totals).all() or np.any(totals<=0):
        raise ValueError('Invalid or zero-total library')
    factors=target_sum/totals
    result=np.log1p(x*factors[None,:])/np.log(log_base)
    if not np.isfinite(result).all():raise ValueError('Nonfinite transformed response')
    return result,dict(method='library_size_log1p',target_sum=float(target_sum),
                       log_base=float(log_base),library_totals=totals,scaling_factors=factors)


def center_from_training(response, cell_groups, training_mask):
    """Apply training group/gene means to all cells, without variance scaling."""
    y=np.asarray(response,dtype=np.float64);groups=np.asarray(cell_groups);train=np.asarray(training_mask)
    if y.ndim!=2 or min(y.shape)==0 or not np.isfinite(y).all():
        raise ValueError('Finite genes-by-cells response required')
    if groups.shape!=(y.shape[1],) or groups.dtype.kind not in 'USiu':
        raise ValueError('Cell-group identity axis required')
    if groups.dtype.kind in 'US' and np.any(groups==''):
        raise ValueError('Empty group name')
    if train.shape!=(y.shape[1],) or train.dtype!=np.bool_ or not train.any():
        raise ValueError('Nonempty boolean training mask required')
    levels=np.unique(groups);means=[];out=y.copy()
    for group in levels:
        own=groups==group;fit=own & train
        if not fit.any():raise ValueError('No training observations for group '+str(group))
        mean=y[:,fit].mean(axis=1);means.append(mean);out[:,own]-=mean[:,None]
    return out,dict(groups=levels,means=np.stack(means,axis=1),training_counts=np.array([np.sum(train & (groups==g)) for g in levels]))
