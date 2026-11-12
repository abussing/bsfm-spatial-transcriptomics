"""Bounded review heuristics, not convergence or effective-sample certificates."""
import numpy as np
from .retained_diagnostics import encode


def sweep_measurements(result,elapsed):
    return dict(seconds=float(elapsed),alpha=result.state.alpha.tolist(),zeta=result.state.zeta.tolist(),
        sigma2=result.state.sigma2.tolist(),
        loading_signal=(result.state.loading**2*result.state.alpha[None,None,:]**2).sum(axis=1).tolist(),
        factors=[dict(index=r['factor_index'],energy=encode(r['transition'].info.block_energy),
            logdensity=float(r['transition'].nuts_state.logdensity),
            gradient_norm=float(np.linalg.norm(r['transition'].nuts_state.logdensity_grad)),
            parameters=np.asarray(r['transition'].position.values[:4]).tolist()) for r in result.factor_diagnostics])


def review_windows(rows,*,window=25):
    """Require the SAME factor/block to fail in both consecutive full windows.

    Tree-limit hits remain an efficiency warning, even if frequent. Conditional
    energies are recorded but never combined into an invalid cross-Gibbs E-BFMI.
    """
    if len(rows)<2*window:return dict(status='collecting',completed=len(rows),flags=[])
    recent=rows[-2*window:];ids=sorted(r['index'] for r in recent[0]['factors'])
    groups=[]
    for part in (recent[:window],recent[window:]):
        mapped=[{r['index']:r for r in row['factors']} for row in part]
        if any(sorted(r)!=ids for r in mapped):raise ValueError('Incomplete health factor diagnostics')
        groups.append({i:dict(acceptance=np.mean([r[i]['acceptance'] for r in mapped],axis=0),
            divergence=np.mean([r[i]['divergent'] for r in mapped],axis=0),
            cap=np.mean([np.asarray(r[i]['leapfrogs'])>=1023 for r in mapped],axis=0)) for i in ids})
    flags=[];summaries=[]
    for i in ids:
        for b,name in enumerate(('field','hyper')):
            values={key:[float(g[i][key][b]) for g in groups] for key in ('acceptance','divergence','cap')}
            reasons=[]
            if all(v>.05 for v in values['divergence']):reasons.append('persistent_divergences')
            if all(v<.6 for v in values['acceptance']):reasons.append('persistent_low_acceptance')
            if reasons:flags.append(dict(factor=i+1,block=name,reasons=reasons))
            summaries.append(dict(factor=i+1,block=name,**values))
    return dict(status='review_required' if flags else 'no_persistent_guard_failure',
        flags=flags,windows=summaries,convergence='not_assessed',
        scope='two consecutive windows; depth limit is warning only')
