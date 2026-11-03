"""Summarize a fixed snapshot of committed production records without pausing the chain."""
import argparse
import json
from pathlib import Path
import numpy as np
from experiment import controllers, target_and_seeds
from bsfm.sampler.run_readaptation import ReadaptationController,parent_endpoint
from bsfm.sampler.retained_records import load_record
from bsfm.sampler.run_storage import read_json,file_record
from bsfm.sampler.holdout_prediction import predict_record

def main(a):
    parent,binding,spec=controllers(a.configuration,a.prepared,a.root,a.model,a.commit)
    _,receipt=parent_endpoint(parent);binding=dict(binding,readaptation_parent=receipt)
    child=ReadaptationController(a.root/a.model/'production',parent.target,parent.loading,parent.eta,
        spec('production_'+a.configuration+'_'+a.model,100,1000,binding),binding,authenticate=parent.authenticate,parent=parent)
    paths=sorted((child.store.segment/'transactions').glob('[0-9]'*12))
    if not paths:raise RuntimeError('No committed production draws yet; bridge draws are excluded')
    selected=np.unique(np.linspace(0,len(paths)-1,min(a.max_draws,len(paths)),dtype=int))
    # Snapshot names and identities before evaluating predictions.
    snapshot=[dict(path=str(paths[i]),receipt=file_record(paths[i]/'prepared.json')) for i in selected]
    with np.load(a.prepared/'scoring.npz',allow_pickle=False) as z:scoring={k:z[k].copy() for k in z.files}
    from experiment import MIRROR,authenticated
    mesh=authenticated(MIRROR/'s10-mesh/sampler-facing.npz','69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0')
    projector=mesh['A_full'][scoring['heldout_full_indices']]
    total=np.zeros_like(scoring['Y']);second=np.zeros_like(total)
    for row in snapshot:
        path=Path(row['path']);record=read_json(path/'prepared.json')
        if record['record']!=file_record(path/'record.npz'):raise ValueError('Committed record bytes changed')
        meta,arrays,_=load_record(path/'record.npz',target=child.target,contract=child.rc,b_sigma2=child.scale)
        if meta['retained_index'] is None:raise ValueError('Non-production record selected')
        mean,var=predict_record(child.target,arrays,projector,scoring['slocs'],scoring['cell_id'],
            rng=np.random.default_rng(np.random.SeedSequence([20261103,int(path.name),1 if a.model=='deep' else 2])))
        total+=mean;second+=var+mean**2
    mean=total/len(snapshot);variance=second/len(snapshot)-mean**2
    output=a.root/'predictions'/a.model/f'snapshot-{len(paths):012d}'
    output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'predictions.npz',mean=mean,variance=variance,
        truth=scoring['Y'],slocs=scoring['slocs'],cell_id=scoring['cell_id'],cell_names=scoring['cell_names'],gene_names=scoring['gene_names'])
    report=dict(commit=a.commit,configuration=a.configuration,model=a.model,
        completed_production_sweeps=len(paths),prediction_draws=len(snapshot),snapshot=snapshot,
        RMSE=float(np.sqrt(np.mean((mean-scoring['Y'])**2))),
        MAE=float(np.mean(abs(mean-scoring['Y']))),
        scope='preliminary full-sample SCT, training-only centering/initialization/fitting; no convergence claim',
        prediction='conditional finite-feature eta at omitted coordinates; conditional full-mesh warp draw for inactive vertices; independent prediction RNG',
        output=file_record(output/'predictions.npz'))
    (output/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('configuration');p.add_argument('prepared',type=Path)
    p.add_argument('root',type=Path);p.add_argument('model',choices=['flat','deep']);p.add_argument('commit')
    p.add_argument('--max-draws',type=int,default=20)
    a=p.parse_args()
    if a.max_draws<1:p.error('max-draws must be positive')
    main(a)
