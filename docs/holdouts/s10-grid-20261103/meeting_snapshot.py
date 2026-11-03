"""Read-only flat production snapshot and held-out conditional means for meeting."""
import json, hashlib, subprocess, datetime, sys
from pathlib import Path
import numpy as np
from scipy.linalg import eigh
from experiment_rule import load_rule
from bsfm.sampler.holdout_prediction import features, conditional_factor
from bsfm.sampler.retained_records import descriptor
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.run_storage import file_record

ROOT=Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea')
CONFIGS=['circles12_diameter1of16','circles12_diameter1of8','circles8_diameter1of16','circles8_diameter1of8']
def read(p):
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}
def main():
    out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=False)
    report={'timestamp':datetime.datetime.now(datetime.timezone.utc).isoformat(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'configurations':[]}
    snapshots={c:sorted((ROOT/c/'flat/production/segments/segment/transactions').glob('[0-9]'*12)) for c in CONFIGS}
    rule=load_rule()
    for c in CONFIGS:
        p=ROOT/c/'prepared';pr=json.loads((p/'prepared.json').read_text())
        for name in ['training.npz','scoring.npz']:
            assert file_record(p/name)==pr['files'][name]
        tr=read(p/'training.npz');sc=read(p/'scoring.npz');center=tr['slocs'].mean(axis=0)
        pt=features(tr['slocs']-center,rule);pq=features(sc['slocs']-center,rule)
        ev,v=eigh(pt.T@pt);bt=pt@v;bq=pq@v
        paths=snapshots[c];assert paths
        draws=[];identities=[];validation=0.
        for i,path in enumerate(paths):
            tx=json.loads((path/'prepared.json').read_text());fr=file_record(path/'record.npz');assert fr==tx['record']
            a=read(path/'record.npz');m=json.loads(str(a.pop('metadata')))
            assert m['logical_sha256']==digest({k:v for k,v in m.items() if k!='logical_sha256'})==tx['record_logical_sha256']
            assert m['status']=='completed' and m['production_sweep']>0 and m['retained_index'] is not None
            assert set(a)==set(m['arrays']) and all(descriptor(x)==m['arrays'][k] for k,x in a.items())
            assert int(path.name)==m['sweep'] and m['contract_sha256']==tx['archive_contract_sha256']
            np.testing.assert_allclose(a['W_cell'],np.broadcast_to(tr['slocs']-center,a['W_cell'].shape),rtol=0,atol=1e-12)
            assert np.all(a['ell_eta']==.14) and np.all((a['zeta']>0)&(a['zeta']<1))
            denom=ev[None,:]+((1-a['zeta'])/a['zeta'])[:,None];assert np.all(denom>0)
            eta=((a['eta']@bt)/denom)@bq.T
            if i==0:
                for k in range(len(a['zeta'])):
                    ref,_=conditional_factor(pt,a['eta'][k],pq,float(a['alpha'][k]),float(a['zeta'][k]))
                    np.testing.assert_allclose(eta[k],ref,rtol=1e-8,atol=1e-8)
                    validation=max(validation,float(np.max(abs(eta[k]-ref))))
            pred=np.empty_like(sc['Y'])
            for ct in range(3):
                mask=sc['cell_id']==ct;pred[:,mask]=a['loading'][ct]@eta[:,mask]
            assert np.isfinite(pred).all();draws.append(pred)
            identities.append({'path':str(path),'record':fr,'sweep':m['sweep']})
        draws=np.stack(draws);mean=draws.mean(axis=0);truth=sc['Y'];err=mean-truth
        dest=out/c;dest.mkdir();np.savez_compressed(dest/'draw_predictions.npz',Yhat=draws,mean=mean,truth=truth,cell_names=sc['cell_names'],gene_names=sc['gene_names'])
        baseline=np.mean(truth**2,axis=1);mse=np.mean(err**2,axis=1)
        offset=sc['training_means'][sc['cell_id']].T
        row={'id':c,'draws':len(paths),'training':len(tr['slocs']),'heldout':len(sc['slocs']),
             'rmse':float(np.sqrt(np.mean(err**2))),'mae':float(np.mean(abs(err))),
             'baseline_rmse':float(np.sqrt(np.mean(truth**2))),
             'gene_rmse':np.sqrt(mse).tolist(),'gene_baseline_rmse':np.sqrt(baseline).tolist(),
             'gene_variance':np.var(truth+offset,axis=1).tolist(),
             'train_xy':tr['slocs'][:,::-1].round(6).tolist(),'train_type':tr['cell_id'].tolist(),
             'test_xy':sc['slocs'][:,::-1].round(6).tolist(),'test_type':sc['cell_id'].tolist(),
             'truth':(truth+offset).round(5).tolist(),'mean':(mean+offset).round(5).tolist(),
             'genes':sc['gene_names'].tolist(),'cell_types':tr['cell_type_names'].tolist(),
             'validation_max_abs':validation,'output':str(dest),'draw_file':file_record(dest/'draw_predictions.npz')}
        (dest/'receipt.json').write_text(json.dumps({'snapshot':identities,**{k:val for k,val in row.items() if k not in ['truth','mean','train_xy','test_xy','train_type','test_type']}},indent=2))
        report['configurations'].append(row);print(c,len(paths),row['rmse'],flush=True)
    (out/'report.json').write_text(json.dumps(report,separators=(',',':')))
    print('REPORT_COMPLETE',out,flush=True)
if __name__=='__main__':main()
