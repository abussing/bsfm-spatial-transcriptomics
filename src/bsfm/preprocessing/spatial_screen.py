"""Generic GP screen recovered from the Johnston review fit_one implementation.

Fits training responses only. Known geometry defines the coordinate transform.
No held-out prediction score is used for selection. This is not a BSFM fit.
"""
import argparse
import json
import importlib.metadata
from pathlib import Path
import warnings
import numpy as np
from .dataset import load_dataset,file_hash,validate
from .gene_selection import expression_eligible


def screen_sample(data,metadata,*,sample,groups,training_cells,genes,config):
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import ConstantKernel,Matern,WhiteKernel
    from threadpoolctl import threadpool_limits
    validate(data,metadata)
    for label,values in [('groups',groups),('genes',genes),('training_cells',training_cells)]:
        if not values or len(values)!=len(set(values)) or any(not isinstance(v,str) or not v for v in values):
            raise ValueError('Explicit unique '+label+' required')
    cap=config['cap'];seed=config['seed'];threads=config['threads']
    if any(type(v) is not int or v<1 for v in (cap,threads)) or type(seed) is not int or not 0<=seed<2**32:
        raise ValueError('Invalid cap/threads/seed')
    if metadata['normalization']['units']!=config['expression_units']:
        raise ValueError('Expression thresholds belong to different response units')
    if type(config['minimum_nonzero']) is not int or config['minimum_nonzero']<1:
        raise ValueError('Positive minimum_nonzero required')
    if not np.isfinite(config['constant_variance_tolerance']) or config['constant_variance_tolerance']<0:
        raise ValueError('Invalid variance tolerance')
    population=np.flatnonzero((data['sample_names']==sample)&np.isin(data['group_names'],groups))
    if not set(training_cells)<=set(data['cell_names'][population]):raise ValueError('Training cells outside declared population')
    if set(data['group_names'][population])!=set(groups):raise ValueError('Missing group')
    lookup={g:i for i,g in enumerate(data['gene_names'])}
    if not set(genes)<=set(lookup):raise ValueError('Unknown genes')
    xy=data['coordinates'];origin=xy[population].min(axis=0);span=float(np.ptp(xy[population],axis=0).max())
    if span<=0:raise ValueError('Zero geometry span')
    X=(xy-origin)/span
    rng=np.random.RandomState(seed);rows=[];chosen={}
    k=config['kernel'];regressor=config['regressor']
    if regressor!={'normalize_y':True,'n_restarts_optimizer':0,'alpha':1e-6}:
        raise ValueError('Unreviewed GP screening regressor settings')
    with threadpool_limits(limits=threads):
        for group in groups:
            own=population[(data['group_names'][population]==group)&np.isin(data['cell_names'][population],training_cells)]
            own=own[np.argsort(data['source_row_indices'][own],kind='stable')]
            if not len(own):raise ValueError('Group has no training cells')
            train=rng.choice(own,min(cap,len(own)),replace=False);chosen[group]=train.tolist()
            response=data['expression'][np.ix_([lookup[g] for g in genes],own)]
            eligibility=expression_eligible(response,**config['expression'])
            for i,gene in enumerate(genes):
                y=response[i];yf=data['expression'][lookup[gene],train]
                status='FIT'
                if not eligibility['eligible'][i]:status='EXPRESSION_INELIGIBLE'
                elif np.var(y)<config['constant_variance_tolerance']:status='CONSTANT'
                elif np.count_nonzero(y)<config['minimum_nonzero']:status='TOO_FEW_NONZERO'
                elif np.var(yf)<config['constant_variance_tolerance']:status='CONSTANT_TRAINING_SUBSET'
                r=dict(sample=sample,gene=gene,celltype=group,
                       animal=str(data['animal_names'][own[0]]) if metadata['animal_identity_known'] else None,
                       status=status,n_population=len(own),n_fit=len(train),
                       spatial_fraction=None,length_scale=None,signal_variance=None,noise_variance=None,warnings=[])
                if status=='FIT':
                    kernel=ConstantKernel(k['constant'],tuple(k['constant_bounds']))*Matern(k['length_scale'],tuple(k['length_scale_bounds']),nu=k['nu'])+WhiteKernel(k['noise'],tuple(k['noise_bounds']))
                    gp=GaussianProcessRegressor(kernel=kernel,**regressor)
                    with warnings.catch_warnings(record=True) as caught:
                        warnings.simplefilter('always');gp.fit(X[train],yf)
                    signal=float(gp.kernel_.k1.k1.constant_value);noise=float(gp.kernel_.k2.noise_level)
                    r.update(spatial_fraction=signal/(signal+noise),length_scale=float(gp.kernel_.k1.k2.length_scale),
                             signal_variance=signal,noise_variance=noise,warnings=[str(w.message) for w in caught])
                rows.append(r)
    return dict(schema='bsfm.gp-screen.v1',rows=rows,training_dataset_indices=chosen,
                coordinate_transform=dict(origin=origin.tolist(),span=span),config=config,
                heldout_expression_used=False,normalization_population=metadata['normalization']['population'])


def aggregate_animals(rows):
    """Median over technical sections, as in recovered extension.report.

    Unknown animals are not replaced by sample IDs. Non-fitted blocks are omitted
    from the screening table; omissions are not zero spatial signal.
    """
    grouped={};seen=set();sample_animals={}
    for r in rows:
        key=(r['sample'],r['gene'],r['celltype'])
        if key in seen:raise ValueError('Duplicate screening block')
        seen.add(key)
        if not r['animal']:raise ValueError('Cannot evaluate animal recurrence without animal identity')
        if sample_animals.setdefault(r['sample'],r['animal'])!=r['animal']:
            raise ValueError('Sample maps to multiple animals')
        if r['status']!='FIT':continue
        value=r['spatial_fraction']
        if value is None or not np.isfinite(value) or not 0<=value<=1:raise ValueError('Invalid fitted spatial fraction')
        grouped.setdefault((r['gene'],r['celltype'],r['animal']),[]).append(value)
    return [dict(gene=g,celltype=t,animal=a,spatial_fraction=float(np.median(v))) for (g,t,a),v in sorted(grouped.items())]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise FileExistsError(a.output)
    d,m=load_dataset(a.dataset,expected_manifest_sha256=a.manifest_sha256)
    recipe=json.loads(a.recipe.read_text(encoding='utf-8'))
    r=screen_sample(d,m,**recipe)
    r.update(dataset_manifest_sha256=a.manifest_sha256,recipe_sha256=file_hash(a.recipe),
             source_sha256=file_hash(__file__),
             versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')})
    with a.output.open('x',encoding='utf-8') as f:json.dump(r,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
