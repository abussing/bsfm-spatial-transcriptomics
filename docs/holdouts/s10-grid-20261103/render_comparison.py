"""Render matched partial deep/flat predictions; run in a plotting environment."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

p=argparse.ArgumentParser();p.add_argument('deep',type=Path);p.add_argument('flat',type=Path);p.add_argument('output',type=Path)
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
with np.load(a.deep/'predictions.npz',allow_pickle=False) as z:deep={k:z[k].copy() for k in z.files}
with np.load(a.flat/'predictions.npz',allow_pickle=False) as z:flat={k:z[k].copy() for k in z.files}
for key in ('truth','slocs','cell_id','cell_names','gene_names'):
    if not np.array_equal(deep[key],flat[key]):raise ValueError('Unmatched prediction cells/genes/targets')
receipts={name:json.loads((path/'receipt.json').read_text()) for name,path in [('deep',a.deep),('flat',a.flat)]}
if receipts['deep']['configuration']!=receipts['flat']['configuration']:raise ValueError('Different hole configurations')
metrics=[]
for gene,name in enumerate(deep['gene_names']):
    fig,axes=plt.subplots(3,3,figsize=(10,8),sharex=True,sharey=True)
    values=[deep['truth'][gene],deep['mean'][gene],flat['mean'][gene]]
    vmin=min(float(v.min()) for v in values);vmax=max(float(v.max()) for v in values)
    for c,label in enumerate(('MIC','AST','OGC')):
        rows=np.flatnonzero(deep['cell_id']==c)
        for j,title in enumerate(('Observed','Deep prediction','Flat prediction')):
            ax=axes[c,j]
            points=ax.scatter(deep['slocs'][rows,1],deep['slocs'][rows,0],c=values[j][rows],s=9,
                cmap='viridis',vmin=vmin,vmax=vmax)
            ax.set_aspect('equal');ax.set_title(f'{label}: {title}',fontsize=10)
        for model,data in [('deep',deep),('flat',flat)]:
            error=data['mean'][gene,rows]-deep['truth'][gene,rows]
            metrics.append(dict(gene=str(name),cell_type=label,model=model,cells=len(rows),
                RMSE=float(np.sqrt(np.mean(error**2))),MAE=float(np.mean(abs(error)))))
    fig.colorbar(points,ax=axes.ravel().tolist(),label='Training-centered SCT response',shrink=.65)
    fig.suptitle(f'{name} | {receipts["deep"]["configuration"]}\n'
        f'Partial production snapshots: deep {receipts["deep"]["completed_production_sweeps"]}, '
        f'flat {receipts["flat"]["completed_production_sweeps"]}\n'
        'Full-sample SCT; no convergence claim',fontsize=11)
    fig.subplots_adjust(top=.83,hspace=.3,wspace=.15)
    fig.savefig(a.output/f'gene-{gene:03d}.png',dpi=150);plt.close(fig)
(a.output/'metrics.json').write_text(json.dumps(dict(sources=receipts,per_gene_type=metrics),indent=2)+'\n')
import html
items='\n'.join(f'<h2>{html.escape(str(name))}</h2><img src="gene-{i:03d}.png" style="max-width:100%">' for i,name in enumerate(deep['gene_names']))
(a.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Partial S10 comparison</title>'
    '<h1>Preliminary S10 deep/flat predictions at omitted cells</h1>'
    '<p>Full-sample SCT; snapshots may have different completed sweep counts. No convergence claim.</p>'+items)
