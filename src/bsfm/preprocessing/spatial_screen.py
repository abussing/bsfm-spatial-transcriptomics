"""Generic GP screen recovered from the Johnston review fit_one implementation.

Fits training responses only. Known geometry defines the coordinate transform.
No held-out prediction score is used for selection. This is not a BSFM fit.
"""
import argparse
import json
import importlib.metadata
from pathlib import Path
import warnings
import hashlib
import os
import platform
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
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


def _json_bytes(value):
    return (json.dumps(value,sort_keys=True,allow_nan=False)+'\n').encode('utf-8')


def _publish(path,value):
    """Atomic file publication; caller holds the checkpoint-directory lock."""
    raw=_json_bytes(value)
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('Existing output differs: '+str(path))
        return
    fd,name=tempfile.mkstemp(prefix='.pending-',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f:f.write(raw);f.flush();os.fsync(f.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def _load_worker(dataset,manifest):
    global _worker_data,_worker_metadata
    _worker_data,_worker_metadata=load_dataset(dataset,expected_manifest_sha256=manifest)


def _screen_worker(spec):
    return screen_sample(_worker_data,_worker_metadata,**spec)


def screen_batched(dataset,manifest,recipe_path,checkpoint,*,batch_size,workers,output):
    """Partition genes only; every batch keeps all groups and identical RNG draws.

    Completed batches survive interruption. Only unpublished batches may be
    recomputed. A stale .lock directory after forced termination needs explicit
    removal after confirming that the previous process and its workers stopped.
    """
    if type(batch_size) is not int or batch_size<1 or type(workers) is not int or workers<1:
        raise ValueError('Positive batch size and workers required')
    recipe_path=Path(recipe_path);checkpoint=Path(checkpoint);output=Path(output)
    recipe=json.loads(recipe_path.read_text(encoding='utf-8'))
    genes=recipe['genes'];groups=recipe['groups']
    if not genes or len(set(genes))!=len(genes):raise ValueError('Unique nonempty gene list required')
    if not groups or len(set(groups))!=len(groups):raise ValueError('Unique nonempty groups required')
    data,metadata=load_dataset(dataset,expected_manifest_sha256=manifest)
    versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')}
    contract=dict(schema='bsfm.gp-screen-batches.v1',dataset_manifest_sha256=manifest,
                  recipe_sha256=file_hash(recipe_path),source_sha256=file_hash(__file__),
                  dependency_sources={name:file_hash(Path(__file__).with_name(name))
                                      for name in ('dataset.py','gene_selection.py','normalization.py')},
                  versions=versions,python=platform.python_version(),platform=platform.platform(),
                  batch_size=batch_size)
    identity=hashlib.sha256(_json_bytes(contract)).hexdigest()
    checkpoint.mkdir(parents=True,exist_ok=True)
    lock=checkpoint/'.lock';lock.mkdir(exist_ok=False)
    try:
        _publish(checkpoint/'contract.json',contract)
        chunks=[genes[i:i+batch_size] for i in range(0,len(genes),batch_size)]
        reports={};pending=[]
        def accept(index,envelope):
            report=envelope['report']
            if envelope['contract_sha256']!=identity or envelope['index']!=index:
                raise ValueError('Batch identity differs')
            if hashlib.sha256(_json_bytes(report)).hexdigest()!=envelope['report_sha256']:
                raise ValueError('Batch checksum differs')
            expected=[(recipe['sample'],gene,group) for group in groups for gene in chunks[index]]
            if [(r['sample'],r['gene'],r['celltype']) for r in report['rows']]!=expected:
                raise ValueError('Batch rows differ')
            reports[index]=report
        def save(index,report):
            envelope=dict(contract_sha256=identity,index=index,report=report,
                          report_sha256=hashlib.sha256(_json_bytes(report)).hexdigest())
            accept(index,envelope)
            _publish(checkpoint/f'batch-{index:06d}.json',envelope)
            print(f'BATCH {index+1}/{len(chunks)} COMPLETE',flush=True)
        for index,chunk in enumerate(chunks):
            path=checkpoint/f'batch-{index:06d}.json'
            if path.exists():accept(index,json.loads(path.read_text(encoding='utf-8')))
            else:pending.append((index,dict(recipe,genes=chunk)))
        print(f'RESUME {len(reports)}/{len(chunks)} batches already complete',flush=True)
        if workers==1:
            for index,spec in pending:save(index,screen_sample(data,metadata,**spec))
        elif pending:
            del data
            with ProcessPoolExecutor(max_workers=workers,initializer=_load_worker,
                                     initargs=(str(dataset),manifest)) as pool:
                tasks={pool.submit(_screen_worker,spec):index for index,spec in pending}
                try:
                    for future in as_completed(tasks):save(tasks[future],future.result())
                except BaseException:
                    for future in tasks:future.cancel()
                    raise
        base={k:v for k,v in reports[0].items() if k!='rows'}
        rows={}
        for report in reports.values():
            if {k:v for k,v in report.items() if k!='rows'}!=base:
                raise ValueError('Batch geometry, sampling or configuration differs')
            rows.update({(r['gene'],r['celltype']):r for r in report['rows']})
        result=dict(base,rows=[rows[g,t] for t in groups for g in genes],
                    dataset_manifest_sha256=manifest,recipe_sha256=contract['recipe_sha256'],
                    source_sha256=contract['source_sha256'],versions=versions,
                    batch_contract_sha256=identity)
        _publish(output,result)
        return result
    finally:
        lock.rmdir()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--recipe',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--checkpoint-dir',type=Path)
    p.add_argument('--batch-size',type=int,default=16)
    p.add_argument('--workers',type=int,default=1)
    a=p.parse_args()
    if a.checkpoint_dir is not None:
        screen_batched(a.dataset,a.manifest_sha256,a.recipe,a.checkpoint_dir,
                       batch_size=a.batch_size,workers=a.workers,output=a.output)
        return
    if a.workers!=1:p.error('--workers requires --checkpoint-dir')
    if a.output.exists():raise FileExistsError(a.output)
    d,m=load_dataset(a.dataset,expected_manifest_sha256=a.manifest_sha256)
    recipe=json.loads(a.recipe.read_text(encoding='utf-8'))
    r=screen_sample(d,m,**recipe)
    r.update(dataset_manifest_sha256=a.manifest_sha256,recipe_sha256=file_hash(a.recipe),
             source_sha256=file_hash(__file__),
             versions={p:importlib.metadata.version(p) for p in ('numpy','scipy','scikit-learn','threadpoolctl')})
    with a.output.open('x',encoding='utf-8') as f:json.dump(r,f,indent=2,allow_nan=False);f.write('\n')


if __name__=='__main__':main()
