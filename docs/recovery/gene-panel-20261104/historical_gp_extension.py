"""Run only newly eligible GP screening tasks with the unchanged review.fit_one.

Install this folder inside the existing HPC gene_review19_20261004_v1 root.
No normalization, no factor-model fitting, no changes to the old72-gene gallery.
"""
import os
for k in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[k]='1'
from pathlib import Path
import sys
import json
import hashlib
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
import time
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
sys.path.insert(0,str(ROOT))
import review


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''):h.update(b)
    return h.hexdigest()


def tables():
    w=pd.read_csv(HERE/'WORKLIST.csv')
    assert len(w)==3331 and not w.duplicated(['section','gene','celltype']).any()
    assert w.action.eq('NEEDS_GP_FIT').sum()==1372
    assert w.action.eq('REUSE_EXISTING_GP').sum()==1959
    assert w.gene.nunique()==137 and w.section.nunique()==19
    assert set(w.celltype).issubset(review.TYPES)
    return w


def verify_code():
    expected=json.loads((HERE/'MANIFEST.json').read_text())
    for name,h in expected['extension_files'].items():
        assert digest(HERE/name)==h, name
    assert digest(ROOT/'review.py')==expected['review_sha256'],'GP implementation changed'
    assert review.OUT==ROOT
    return expected


def validate(section=None):
    expected=verify_code();w=tables()
    if section:w=w[w.section.eq(section)]
    assert len(w)>0
    n=0
    for sec,rows in w.groupby('section',sort=False):
        p=ROOT/'sections'/sec/'input.npz'
        assert digest(p)==expected['inputs'][sec],sec
        with np.load(p) as z:
            genes,Y,types=z['genes'],z['Y'],z['types']
            source=z['source_rows']
        index={g:i for i,g in enumerate(genes)}
        for r in rows.itertuples():
            own=np.flatnonzero(types==r.celltype);y=Y[index[r.gene],own]
            assert np.isfinite(y).all() and np.mean(y!=0)>=.3 and np.quantile(y,.9)>=1
            assert np.var(y)>=1e-12,(sec,r.gene,r.celltype,'old fitter constancy gate')
            p=ROOT/'sections'/sec/'fits'/f'{r.gene}__{r.celltype}.npz'
            if r.action=='REUSE_EXISTING_GP':
                assert digest(p)==expected['reuse_fits'][f'{sec}/{p.name}'],p
            if p.exists():
                with np.load(p) as f:
                    assert str(f['status']) in ['FIT','REUSED_FULL_DATA'],(p,'existing non-fit; manual review required')
                    np.testing.assert_array_equal(f['indices'],own)
                    assert np.isfinite(f['mean']).all() and len(f['mean'])==len(own)
                    if str(f['status'])=='FIT':
                        assert set(f['train_source_rows']).issubset(set(source[own]))
            n+=1
        print('VALIDATED',sec,len(rows),flush=True)
    print('EXTENSION VALIDATION PASS',n,'records',flush=True)


def fit(section,jobs,limit):
    validate(section)
    w=tables();w=w[w.section.eq(section)&w.action.eq('NEEDS_GP_FIT')]
    assert len(w)>0
    tasks=[(r.section,r.gene,r.celltype,1500,False) for r in w.itertuples()
           if not (ROOT/'sections'/r.section/'fits'/f'{r.gene}__{r.celltype}.npz').exists()]
    if limit:tasks=tasks[:limit]
    print('EXTENSION GP START',section,'tasks',len(tasks),'workers',jobs,'cap1500 Matern2.5',flush=True)
    failures=[];start=time.time()
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        futures=[pool.submit(review.fit_one,t) for t in tasks]
        for i,f in enumerate(as_completed(futures),1):
            result=f.result()
            if result[0] not in ['FIT','EXISTS']:failures.append(result)
            print('EXTENSION GP',i,'/',len(tasks),*result,'elapsed',round(time.time()-start,1),flush=True)
    if failures:raise RuntimeError(f'Unsuccessful tasks: {failures}')
    validate(section)
    print('EXTENSION SECTION COMPLETE',section,flush=True)


def report():
    validate();w=tables();rows=[]
    for sec,ss in w.groupby('section',sort=False):
        with np.load(ROOT/'sections'/sec/'input.npz') as z:
            Y,genes,types,source=z['Y'],z['genes'],z['types'],z['source_rows']
        ix={g:i for i,g in enumerate(genes)}
        for r in ss.itertuples():
            p=ROOT/'sections'/sec/'fits'/f'{r.gene}__{r.celltype}.npz'
            assert p.exists(),p
            own=np.flatnonzero(types==r.celltype);y=Y[ix[r.gene],own]
            with np.load(p) as f:
                pred=f['mean'];status=str(f['status'])
                out=dict(section=sec,gene=r.gene,celltype=r.celltype,animal=r.animal,genotype=r.genotype,
                    source_action=r.action,status=status,N=len(y),spatial_fraction=float(f['spatial_fraction']),
                    length_scale=float(f['length_scale']),n_train=int(f['n_train']),warning=str(f['warning']),
                    heldout_n=0,heldout_gain=np.nan,heldout_corr=np.nan,
                    smoothed_variance_ratio=float(np.var(pred)/np.var(y)))
                if status=='FIT':
                    tr=np.isin(source[own],f['train_source_rows'])
                    assert tr.sum()==out['n_train']
                    out['heldout_n']=int((~tr).sum())
                    if out['heldout_n']>=30:
                        baseline=np.mean((y[~tr]-np.mean(y[tr]))**2)
                        out['heldout_gain']=float(1-np.mean((y[~tr]-pred[~tr])**2)/baseline)
                        if np.std(pred[~tr])>1e-12 and np.std(y[~tr])>1e-12:
                            out['heldout_corr']=float(np.corrcoef(y[~tr],pred[~tr])[0,1])
                rows.append(out)
    d=pd.DataFrame(rows);d.to_csv(HERE/'EXPANDED_GP_RESULTS.csv',index=False)
    a=d.groupby(['gene','celltype','animal'],as_index=False).agg(
        spatial_fraction=('spatial_fraction','median'),heldout_gain=('heldout_gain','median'))
    a.to_csv(HERE/'EXPANDED_GP_ANIMAL_SUMMARY.csv',index=False)
    counts=dict(records=len(d),genes=d.gene.nunique(),new_fits=int(d.source_action.eq('NEEDS_GP_FIT').sum()),
        reused=int(d.source_action.eq('REUSE_EXISTING_GP').sum()),all_complete=True,
        scope='Only expression-qualifying blocks. Missing types/sections are not failed GP fits. No spatial threshold imposed.',
        heldout_caveat='Random-location within-section check; not spatial-block or independent-animal validation.')
    (HERE/'RESULT_QC.json').write_text(json.dumps(counts,indent=2)+'\n')
    print('EXPANDED GP REPORT COMPLETE',json.dumps(counts),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['validate','fit','report'])
    p.add_argument('--section');p.add_argument('--jobs',type=int,default=4);p.add_argument('--limit',type=int)
    a=p.parse_args()
    if a.action=='validate':validate(a.section)
    elif a.action=='fit':
        assert a.section and 1<=a.jobs<=4
        fit(a.section,a.jobs,a.limit)
    else:report()
