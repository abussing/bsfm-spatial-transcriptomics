"""Portable dataset contract and training/scoring response preparation.

Import adapters supply exact identity arrays and declared transformation metadata.
This layer never guesses normalization, animal IDs, coordinate units or genes.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from .normalization import center_from_training

KEYS=('expression','coordinates','gene_names','cell_names','group_names',
      'sample_names','animal_names','source_row_indices')


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def names(x,length,label,*,unique=False,allow_empty=False):
    if x.shape!=(length,) or x.dtype.kind!='U':
        raise ValueError('Unicode identity axis required: '+label)
    if not allow_empty and any(not v.strip() for v in x):
        raise ValueError('Empty identity: '+label)
    if unique and len(set(x))!=length:raise ValueError('Duplicate '+label)


def validate(data,metadata):
    if set(data)!=set(KEYS):raise ValueError('Dataset array fields differ')
    if metadata.get('schema')!='bsfm.dataset.v1':raise ValueError('Dataset schema')
    if not isinstance(metadata.get('dataset_id'),str) or not metadata['dataset_id'].strip():
        raise ValueError('Dataset identity required')
    for field in ('coordinate_units','normalization'):
        if field not in metadata:raise ValueError('Missing '+field)
    if not isinstance(metadata['coordinate_units'],str) or not metadata['coordinate_units'].strip():
        raise ValueError('Explicit coordinate units required; unknown must be labeled')
    norm=metadata['normalization']
    if not isinstance(norm,dict) or norm.get('response')!='uncentered_normalized':
        raise ValueError('This preparation requires declared uncentered normalized response')
    for field in ('method','units','population','evidence'):
        if not isinstance(norm.get(field),str) or not norm[field].strip():
            raise ValueError('Normalization declaration requires '+field)
    y=data['expression'];xy=data['coordinates']
    if y.ndim!=2 or min(y.shape)==0 or y.dtype!=np.float64 or not np.isfinite(y).all():
        raise ValueError('Float64 finite genes-by-cells expression required')
    g,n=y.shape
    if xy.shape!=(n,2) or xy.dtype!=np.float64 or not np.isfinite(xy).all():
        raise ValueError('Finite float64 cells-by-two coordinates required')
    names(data['gene_names'],g,'genes',unique=True)
    names(data['cell_names'],n,'cells',unique=True)
    for field in ('group_names','sample_names'):names(data[field],n,field)
    known=metadata.get('animal_identity_known')
    if type(known) is not bool:raise ValueError('Explicit animal_identity_known required')
    names(data['animal_names'],n,'animals',allow_empty=not known)
    if not known and np.any(data['animal_names']!=''):
        raise ValueError('Unknown animal identities must remain empty, not fabricated')
    rows=data['source_row_indices']
    if rows.shape!=(n,) or rows.dtype.kind not in 'iu' or np.any(rows<0):
        raise ValueError('Nonnegative integer source rows required')
    if len(set(zip(data['sample_names'],rows.tolist())))!=n:
        raise ValueError('Duplicate sample/source-row identity')
    if known:
        for sample in np.unique(data['sample_names']):
            if len(np.unique(data['animal_names'][data['sample_names']==sample]))!=1:
                raise ValueError('Sample maps to multiple animals')


def write_dataset(destination,data,metadata,*,sources):
    """Publish a fresh immutable directory; source identities are mandatory."""
    validate(data,metadata)
    if not sources or any(not isinstance(s,dict) or set(s)!={'path','sha256'}
                          or not isinstance(s['path'],str) or not s['path']
                          or not isinstance(s['sha256'],str) or len(s['sha256'])!=64
                          or any(c not in '0123456789abcdef' for c in s['sha256']) for s in sources):
        raise ValueError('Explicit source paths and SHA256 identities required')
    destination=Path(destination)
    if destination.exists():raise FileExistsError(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.dataset-',dir=destination.parent))
    np.savez_compressed(stage/'dataset.npz',**data)
    receipt=dict(metadata,artifact_sha256=file_hash(stage/'dataset.npz'),sources=sources,
                 dimensions=dict(genes=data['expression'].shape[0],cells=data['expression'].shape[1]))
    (stage/'dataset.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.rename(stage,destination)
    return receipt


def load_dataset(root,*,expected_manifest_sha256):
    """Verify the caller's pinned manifest and its exact NPZ bytes before loading."""
    root=Path(root)
    if file_hash(root/'dataset.json')!=expected_manifest_sha256:raise ValueError('Dataset manifest changed')
    metadata=json.loads((root/'dataset.json').read_text(encoding='utf-8'))
    if file_hash(root/'dataset.npz')!=metadata['artifact_sha256']:raise ValueError('Dataset bytes changed')
    with np.load(root/'dataset.npz',allow_pickle=False) as z:
        if len(z.files)!=len(set(z.files)):raise ValueError('Duplicate NPZ members')
        data={k:z[k].copy() for k in z.files}
    validate(data,metadata)
    if metadata['dimensions']!=dict(genes=data['expression'].shape[0],cells=data['expression'].shape[1]):
        raise ValueError('Dataset dimension receipt changed')
    return data,metadata


def prepare_response(data,metadata,*,sample,groups,genes,training_cells,heldout_cells):
    """Prepare one sample, fixed named groups/genes and explicit disjoint splits.

    Geometry normalization uses all selected-group cells in the sample (fixed
    design); expression centering uses training cells only. Raw coordinates and
    biological identities remain in the dataset. No normalization or selection
    based on held-out outcomes occurs here.
    """
    validate(data,metadata)
    for label,items in [('groups',groups),('genes',genes),('training_cells',training_cells),('heldout_cells',heldout_cells)]:
        if not isinstance(items,(list,tuple)) or len(set(items))!=len(items) or any(not isinstance(x,str) or not x for x in items):
            raise ValueError('Explicit unique names required: '+label)
    if not groups or not genes or not training_cells:raise ValueError('Empty modeling selection')
    if set(training_cells)&set(heldout_cells):raise ValueError('Train/test overlap')
    lookup={g:i for i,g in enumerate(data['gene_names'])}
    if not set(genes)<=set(lookup):raise ValueError('Unknown genes')
    own=(data['sample_names']==sample)&np.isin(data['group_names'],groups)
    population=np.flatnonzero(own)
    if not len(population) or set(data['group_names'][population])!=set(groups):raise ValueError('Missing sample/group')
    selected=set(training_cells)|set(heldout_cells)
    if not selected<=set(data['cell_names'][population]):raise ValueError('Split outside declared sample/groups')
    xy=data['coordinates'][population];origin=xy.min(axis=0);scale=float(np.ptp(xy,axis=0).max())
    if scale<=0:raise ValueError('Zero coordinate span')
    # Existing sampler contract requires increasing source rows within group.
    blocks=[population[data['group_names'][population]==g] for g in groups]
    ordered=np.concatenate([b[np.argsort(data['source_row_indices'][b],kind='stable')] for b in blocks])
    train=ordered[np.isin(data['cell_names'][ordered],training_cells)]
    test=ordered[np.isin(data['cell_names'][ordered],heldout_cells)]
    indices=np.concatenate([train,test]);gidx=np.array([lookup[g] for g in genes])
    mask=np.arange(len(indices))<len(train)
    centered,centering=center_from_training(data['expression'][np.ix_(gidx,indices)],data['group_names'][indices],mask)
    code={g:i for i,g in enumerate(groups)}
    def bank(rows,y):
        return dict(Y=y,slocs=(data['coordinates'][rows]-origin)/scale,
            cell_id=np.array([code[g] for g in data['group_names'][rows]],dtype=np.int64),
            cell_names=data['cell_names'][rows].copy(),source_row_indices=data['source_row_indices'][rows].copy(),
            gene_names=np.array(genes),cell_type_names=np.array(groups))
    return bank(train,centered[:,:len(train)]),bank(test,centered[:,len(train):]),dict(
        dataset_id=metadata['dataset_id'],sample=sample,groups=groups,genes=genes,
        normalization=metadata['normalization'],coordinate_units=metadata['coordinate_units'],
        coordinate_transform=dict(origin=origin.tolist(),scale=scale,population='all declared groups in selected sample'),
        centering=dict(groups=centering['groups'].tolist(),means=centering['means'].tolist(),training_counts=centering['training_counts'].tolist()),
        geometry_dataset_indices=population.tolist(),training_dataset_indices=train.tolist(),heldout_dataset_indices=test.tolist(),
        heldout_preprocessing_independence='not_inferred_from_imported_normalization')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dataset',type=Path,required=True);p.add_argument('--manifest-sha256',required=True)
    p.add_argument('--selection',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--gpinit-contract',action='store_true',
                   help='Also export the existing authenticated GP/SVD input contract (requires GPINIT dependencies)')
    a=p.parse_args();data,meta=load_dataset(a.dataset,expected_manifest_sha256=a.manifest_sha256)
    selection=json.loads(a.selection.read_text(encoding='utf-8'))
    train,test,receipt=prepare_response(data,meta,**selection)
    if a.gpinit_contract:
        from bsfm.initialization import gp_svd
        gp_svd.validate(train,1,1,0)
    if a.output.exists():raise FileExistsError(a.output)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.response-',dir=a.output.parent))
    np.savez_compressed(stage/'training.npz',**train);np.savez_compressed(stage/'scoring.npz',**test)
    receipt.update(dataset_manifest_sha256=a.manifest_sha256,selection_sha256=file_hash(a.selection),
                   files={n:file_hash(stage/n) for n in ('training.npz','scoring.npz')})
    if a.gpinit_contract:
        contract=dict(schema='bsfm.gpinit-input.v1',response='final_centered_Y',
            source_sha256=file_hash(stage/'training.npz'),arrays=gp_svd.identities(train),
            dataset_manifest_sha256=a.manifest_sha256,selection_sha256=file_hash(a.selection),
            coordinate_transform=receipt['coordinate_transform'],normalization=receipt['normalization'],
            centering=receipt['centering'])
        (stage/'gpinit-input.json').write_text(json.dumps(contract,indent=2,allow_nan=False)+'\n',encoding='utf-8')
        # Use the actual consumer's byte/order checks before publication.
        gp_svd.load_input(stage/'training.npz',contract)
        receipt['files']['gpinit-input.json']=file_hash(stage/'gpinit-input.json')
    (stage/'response.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    os.rename(stage,a.output)


if __name__=='__main__':main()
