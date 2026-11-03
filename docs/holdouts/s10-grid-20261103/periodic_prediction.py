"""Read committed periodic production draws; atomically update compact scores.

CPU sidecar, independent prediction RNG. No chain writes or checkpoint reads.
Pointwise Gaussian-mixture log density is not a joint multi-gene/hole density.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import numpy as np
from experiment import clean,target_and_seeds,MIRROR,authenticated
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.retained_contract import build_retained_contract
from bsfm.sampler.retained_records import descriptor
from bsfm.sampler.run_storage import read_json,file_record,writer
from bsfm.sampler.holdout_prediction import predict_record
from bsfm.sampler.predictive_summary import PredictiveSummary


def update(prepared,root,model,commit):
    clean(commit)
    segment=root/model/'production/segments/segment'
    if not (segment/'genesis/receipt.json').exists():return None
    spec=read_json(root/model/'production/run-spec.json')
    if spec['software']['git_commit']!=commit:raise ValueError('Scoring source commit mismatch')
    target,_,_,_=target_and_seeds(prepared,model,segment/'genesis/endpoint.npz')
    scale=.25*np.var(target.inputs.arrays['Y'],axis=1)
    contract=build_retained_contract(target,b_sigma2=scale,software=spec['software'],
        expected_software_sha256=digest(spec['software']),chain_id=spec['chain_id'],save_every=spec['save_every'],
        settling_sweeps=spec['settling_sweeps'],final_sweep=spec['final_sweep'])
    with np.load(prepared/'scoring.npz',allow_pickle=False) as z:scoring={k:z[k].copy() for k in z.files}
    identity=dict(commit=commit,spec_sha256=digest(spec),scoring=file_record(prepared/'scoring.npz'),
                  model=model,rule='pointwise_normal_mixture_v1_one_conditional_warp_draw_per_posterior_draw')
    summary=PredictiveSummary(scoring['Y']);seen=[]
    out=root/'predictions'/model;out.mkdir(parents=True,exist_ok=True);latest=out/'latest.npz'
    if latest.exists():
        with np.load(latest,allow_pickle=False) as z:
            meta=json.loads(str(z['metadata']))
            if meta['identity']!=identity:raise ValueError('Prediction summary identity changed')
            seen=meta['draws'];summary.count=len(seen)
            summary.mean=z['mean'].copy();summary.second=z['second'].copy()
            summary.log_density_sum=z['log_density_sum'].copy()
    paths=sorted((segment/'boundaries').glob('[0-9]'*12))
    rows=[]
    for path in paths:
        r=read_json(path/'receipt.json')
        if r['sha256']!=digest({k:v for k,v in r.items() if k!='sha256'}) or r['spec_sha256']!=digest(spec):
            raise ValueError('Invalid committed prediction source receipt')
        rows.append(dict(sweep=int(path.name),receipt=file_record(path/'receipt.json')))
    if rows[:len(seen)]!=seen:raise ValueError('Previously scored source changed')
    if len(rows)==len(seen):return summary.count
    mesh=authenticated(MIRROR/'s10-mesh/sampler-facing.npz','69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0')
    projector=mesh['A_full'][scoring['heldout_full_indices']]
    for path,row in zip(paths[len(seen):],rows[len(seen):]):
        receipt=read_json(path/'receipt.json')
        if file_record(path/'record.npz')!=receipt['files']['record.npz']:raise ValueError('Retained draw changed')
        with np.load(path/'record.npz',allow_pickle=False) as z:
            if len(z.files)!=len(set(z.files)):raise ValueError('Duplicate record member')
            arrays={k:z[k].copy() for k in z.files}
        meta=json.loads(str(arrays.pop('metadata')))
        if (meta['logical_sha256']!=digest({k:v for k,v in meta.items() if k!='logical_sha256'})
                or meta['contract_sha256']!=contract.sha256 or meta['sweep']!=row['sweep']
                or meta['retained_index']!=summary.count+1 or set(arrays)!=set(meta['arrays'])):
            raise ValueError('Retained prediction identity mismatch')
        for key,value in arrays.items():
            if descriptor(value)!=meta['arrays'][key]:raise ValueError('Retained array changed')
        mean,var=predict_record(target,arrays,projector,scoring['slocs'],scoring['cell_id'],
            rng=np.random.default_rng(np.random.SeedSequence([20261103,row['sweep'],1 if model=='deep' else 2])))
        summary.update(mean,var);seen.append(row)
        values=summary.arrays();logp=values['pointwise_log_predictive_density']
        metadata=dict(identity=identity,draws=seen,prediction_draws=summary.count,
            last_production_sweep=row['sweep'],RMSE=float(np.sqrt(np.mean((values['mean']-scoring['Y'])**2))),
            MAE=float(np.mean(abs(values['mean']-scoring['Y']))),
            mean_pointwise_log_predictive_density=float(logp.mean()),sum_pointwise_log_predictive_density=float(logp.sum()),
            scope='Preliminary full-sample SCT; pointwise marginals, not joint hole likelihood; no convergence claim')
        fd,tmp=tempfile.mkstemp(prefix='.prediction-',suffix='.npz',dir=out)
        with os.fdopen(fd,'wb') as f:
            np.savez_compressed(f,**values,second=summary.second,log_density_sum=summary.log_density_sum,
                truth=scoring['Y'],slocs=scoring['slocs'],cell_id=scoring['cell_id'],cell_names=scoring['cell_names'],
                gene_names=scoring['gene_names'],metadata=np.array(json.dumps(metadata,sort_keys=True)))
            f.flush();os.fsync(f.fileno())
        os.replace(tmp,latest)
        print('PREDICTIVE_METRICS',model,'draws',summary.count,'sweep',row['sweep'],
              'mean_pointwise_log_density',metadata['mean_pointwise_log_predictive_density'],flush=True)
    return summary.count


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('prepared',type=Path);p.add_argument('root',type=Path)
    p.add_argument('model',choices=['deep','flat']);p.add_argument('commit');p.add_argument('--watch',action='store_true')
    a=p.parse_args()
    while True:
        with writer(a.root/'predictions'/a.model):
            update(a.prepared,a.root,a.model,a.commit)
        if not a.watch or (a.root/a.model/'production/segments/segment/completion.json').exists():break
        time.sleep(60)
