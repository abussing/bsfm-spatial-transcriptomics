"""Explicit preliminary full-SCT holdout runs: preparation, bridge, retuning, production."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import numpy as np
from bsfm.sampler.contracts import ModelInput, input_identity, logical_hash
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.run_storage import file_record, read_json, write_json
from bsfm.sampler.run_inputs import authenticate_environment
from bsfm.sampler.run_chart import geometry_from_genesis
from bsfm.sampler.warp import WarpGeometry, mesh_identity
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.flat_control import FlatTarget, FlatTransition
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_readaptation import ReadaptationController, parent_endpoint
from experiment_rule import load_rule

REPO=Path(__file__).resolve().parents[3]
MIRROR=Path('/work/abussing/bsfm-consolidation/canonical-artifacts-20261103')
SPLITS=Path('/work/abussing/bsfm-consolidation/evidence/s10-grid-20261103/split-indices.npz')
CONFIGS=('circles12_diameter1of16','circles12_diameter1of8','circles8_diameter1of16','circles8_diameter1of8')

def authenticated(path,sha):
    if file_record(path)['sha256']!=sha:raise ValueError('Changed input '+str(path))
    with np.load(path,allow_pickle=False) as z:return {k:z[k].copy() for k in z.files}

def clean(commit):
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()!=commit:
        raise ValueError('Wrong generating commit')
    if subprocess.check_output(['git','status','--porcelain'],cwd=REPO,text=True).strip():raise ValueError('Dirty checkout')

def prepare(config, root, commit):
    from bsfm.initialization.gp_svd import fit, save, CONFIG
    clean(commit);root=Path(root);root.mkdir(parents=True,exist_ok=True)
    if (root/'prepared.json').exists():
        receipt=read_json(root/'prepared.json')
        if receipt['commit']!=commit or receipt['configuration']!=config:raise ValueError('Preparation provenance changed')
        for name,record in receipt['files'].items():
            if file_record(root/name)!=record:raise ValueError('Prepared file changed')
        return receipt
    data=authenticated(MIRROR/'s10-preparation-v2/prepared/model-input.npz','fc9478949f06d5c4c53e77caeb25426eba84b5df93a95c32335b638f912e83f3')
    splits=authenticated(SPLITS,'fa7e24d4d4a8a7b336975ddc05571d895f5957bde694b9c646ec0ccb2e5c7cdd')
    train=splits[config+'_training_full_indices']; test=splits[config+'_heldout_full_indices']
    if len(np.intersect1d(train,test)) or len(train)+len(test)!=4712:raise ValueError('Split overlap/membership')
    selected={k:v.copy() for k,v in data.items()}
    selected['Y']=data['Y'][:,train].copy()
    for k in ('slocs','cell_id','cell_names','source_row_indices'):selected[k]=data[k][train].copy()
    means=np.stack([selected['Y'][:,selected['cell_id']==c].mean(axis=1) for c in range(3)])
    for c in range(3):selected['Y'][:,selected['cell_id']==c]-=means[c,:,None]
    np.savez_compressed(root/'training.npz',**selected)
    # Scoring targets are kept outside the training/initialization input.
    scoring=data['Y'][:,test].copy()
    for c in range(3):scoring[:,data['cell_id'][test]==c]-=means[c,:,None]
    np.savez_compressed(root/'scoring.npz',Y=scoring,cell_id=data['cell_id'][test],
        slocs=data['slocs'][test],cell_names=data['cell_names'][test],gene_names=data['gene_names'],
        training_means=means,training_full_indices=train,heldout_full_indices=test)
    gpconfig=read_json(CONFIG)
    # The HPC SciPy Cholesky crashes when this build is switched to four BLAS
    # threads. Preserve the GP algorithm and use the sampler's stable one-thread
    # library setting. The report records the actual thread limit and libraries.
    gpconfig['threads']=1
    seeds,diagnostics=fit(selected,factors=12,nfit=250,seed=20261103,config=gpconfig)
    save(root/'gpinit',seeds,diagnostics,provenance=dict(commit=commit,configuration=config,
        source=file_record(root/'training.npz'),training_only=True,full_sample_SCT=True))
    receipt=dict(schema='bsfm.preliminary-holdout-preparation.v1',commit=commit,configuration=config,
        full_sample_SCT=True,training_only_centering=True,training_only_GPINIT=True,primary_holdout_scoring_eligible=False,
        K=12,L=14,nfit=250,seed=20261103,genes=91,types=3,
        training_full_indices=train.tolist(),heldout_full_indices=test.tolist(),
        files={n:file_record(root/n) for n in ('training.npz','scoring.npz','gpinit/gpinit.npz','gpinit/certificate.json')})
    write_json(root/'prepared.json',receipt);return receipt

def target_and_seeds(prepared,model,genesis=None):
    receipt=read_json(prepared/'prepared.json')
    for name,record in receipt['files'].items():
        if file_record(prepared/name)!=record:raise ValueError('Prepared artifact changed')
    with np.load(prepared/'training.npz',allow_pickle=False) as z:data={k:z[k].copy() for k in z.files}
    inputs=ModelInput.authenticate(data,input_identity(data,section='S10__WT5',
        response_sha256=receipt['files']['training.npz']['sha256'],coordinate_system='october26_glial_min_max_span'))
    sha='69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0'
    m=authenticated(MIRROR/'s10-mesh/sampler-facing.npz',sha);rows=np.asarray(receipt['training_full_indices'])
    if not np.array_equal(m['source_rows'][rows],data['source_row_indices']):raise ValueError('Mesh/source join')
    projector=m['A_full'][rows].copy()
    arrays=dict(terms=np.stack([m['fem_C']]+[m[f'fem_g{i}'] for i in range(1,7)]),vertices=m['mesh_vertices'],
        projector=projector,locations=m['slocs'][rows],active_indices=np.flatnonzero(np.any(projector!=0,axis=0)),
        source_rows=m['source_rows'][rows],vertex_ids=np.array([f'vertex-{i}' for i in range(len(m['mesh_vertices']))]),cell_ids=data['cell_names'])
    identity=mesh_identity(arrays,section='S10__WT5',mesh_sha256=sha)
    geometry=geometry_from_genesis(arrays,identity,genesis) if genesis is not None and genesis.exists() else WarpGeometry.authenticate(arrays,identity)
    cls=FlatTarget if model=='flat' else DirectWTarget
    target=cls(inputs,geometry,load_rule(),factor_ids=tuple(f'factor-{i:03d}' for i in range(1,13)))
    with np.load(prepared/'gpinit/gpinit.npz',allow_pickle=False) as z:loading=z['Lam_seed'].copy();eta=z['eta_seed'].copy()
    return target,loading,eta,receipt

def use_incremental_store(controller):
    from bsfm.sampler.run_incremental import IncrementalTransactions
    controller.store=IncrementalTransactions(controller.store.root,controller.target,
        controller.cp,controller.rc,controller.scale,controller.spec,controller.store.input_receipt)
    return controller


def controllers(config,prepared,output,model,commit,*,runtime_auth=authenticate_environment,incremental=False):
    clean(commit); environment=runtime_auth()
    bridge=Path(output)/model/'bridge'
    target,loading,eta,receipt=target_and_seeds(Path(prepared),model,bridge/'segments/segment/genesis/endpoint.npz')
    binding=dict(preparation=receipt,model=model,target=target.identity,spectral_identity=target.geometry.spectral_identity)
    def auth():
        clean(commit);target._validate_identities()
        if runtime_auth()!=environment:raise ValueError('Runtime environment changed')
        if read_json(Path(prepared)/'prepared.json')!=receipt:raise ValueError('Preparation changed')
        for name,record in receipt['files'].items():
            if file_record(Path(prepared)/name)!=record:raise ValueError('Prepared input changed')
    def spec(run_id,warmup,sweeps,bind):
        s=dict(schema='bsfm.local-run.v1',run_id=run_id,segment_id='segment',chain_id='chain',
            factor_ids=list(target.factor_ids),seed=20261103,warmup_steps=warmup,settling_sweeps=0,
            production_sweeps=sweeps,final_sweep=sweeps,save_every=1,checkpoint_every=1,
            mode='exact_resume',input_sha256=digest(bind))
        config_identity=dict(s,storage_validation='incremental_lease_v1' if incremental else 'strict_history_v1')
        s['software']=dict(git_commit=commit,clean_tree=True,run_config_sha256=digest(config_identity),
            environment_lock_sha256=environment['lock']['sha256'],environment_identity=digest(environment))
        return s
    parent=RunController(bridge,target,loading,eta,spec('bridge_'+config+'_'+model,50,50,binding),binding,authenticate=auth)
    if model=='flat':parent.layer.split=FlatTransition(target)
    if incremental:use_incremental_store(parent)
    return parent,binding,spec

def run(config,prepared,output,model,commit,*,runtime_auth=authenticate_environment,incremental=False):
    parent,binding,spec=controllers(config,prepared,output,model,commit,runtime_auth=runtime_auth,incremental=incremental)
    print('PHASE initial tuning 50/factor then bridge 50 sweeps',config,model,flush=True)
    parent.run()
    print('PHASE bridge complete; retuning 100/factor then production 1000 sweeps',config,model,flush=True)
    _,receipt=parent_endpoint(parent)
    binding=dict(binding,readaptation_parent=receipt)
    child=ReadaptationController(Path(output)/model/'production',parent.target,parent.loading,parent.eta,
        spec('production_'+config+'_'+model,100,1000,binding),binding,authenticate=parent.authenticate,parent=parent)
    if model=='flat':child.layer.split=FlatTransition(parent.target)
    if incremental:use_incremental_store(child)
    print(json.dumps(child.run()),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['prepare','run']);p.add_argument('configuration',choices=CONFIGS)
    p.add_argument('prepared',type=Path);p.add_argument('output',type=Path);p.add_argument('model',choices=['deep','flat']);p.add_argument('commit')
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.configuration,a.prepared,a.commit)
    else:run(a.configuration,a.prepared,a.output,a.model,a.commit)
