"""Closed-file candidate checks and same-filesystem atomic promotion."""
import os
from pathlib import Path
import uuid
import h5py
import jsonschema
import numpy as np
from scipy import sparse
from .identities import require,read_json,write_json,sha,file_record,logical,REPO
from .geometry import triangles,diagnostics
from .projectors import validate as validate_projector,active,project
from .fem import assemble,validate as validate_fem

MATRICES=['projector','mass','stiffness']
INTEGER_ARRAYS=['vertex_ids','triangles','regions','active','all_rows','model_rows','model_all_index','model_types']
FLOAT_ARRAYS=['vertices','support','collar','outer','eigenvalues','eigenvectors','raw_all','raw_model','numerical_all','numerical_model']
STRING_ARRAYS=['all_ids','model_ids']


def new_attempt(root,name):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    require(not (root/name).exists(),'Finalized destination already exists')
    attempt=root/('.attempt-'+name+'-'+uuid.uuid4().hex);attempt.mkdir()
    return attempt


def save_payload(path,arrays,matrices):
    with h5py.File(path,'x') as f:
        f.attrs['triangle_index_base']=0;f.attrs['schema']='bsfm.mesh.phase0.payload.v1'
        for name,value in arrays.items():
            a=np.asarray(value)
            if a.dtype.kind in 'USO':f.create_dataset(name,data=a.astype(object),dtype=h5py.string_dtype('utf-8'))
            else:f.create_dataset(name,data=a,compression='gzip',shuffle=True)
        for name,a in matrices.items():
            a=a.tocsr(copy=True);a.sum_duplicates();a.eliminate_zeros();a.sort_indices()
            g=f.create_group(name);g.attrs['shape']=a.shape;g.attrs['index_base']=0
            for k,v in [('data',a.data.astype('<f8')),('indices',a.indices.astype('<i8')),('indptr',a.indptr.astype('<i8'))]:g.create_dataset(k,data=v)


def load_payload(path):
    arrays={};matrices={};hashes={}
    with h5py.File(path,'r') as f:
        require(f.attrs['schema']=='bsfm.mesh.phase0.payload.v1' and f.attrs['triangle_index_base']==0,'Payload schema/index base')
        for name,obj in f.items():
            if isinstance(obj,h5py.Group):
                require(name in MATRICES and obj.attrs['index_base']==0,'Unknown sparse payload')
                data=obj['data'][:];idx=obj['indices'][:];ptr=obj['indptr'][:];shape=tuple(map(int,obj.attrs['shape']))
                require(len(ptr)==shape[0]+1 and ptr[0]==0 and ptr[-1]==len(data) and np.all(np.diff(ptr)>=0),'Sparse pointers')
                require(len(idx)==len(data) and np.all((idx>=0)&(idx<shape[1])) and np.isfinite(data).all(),'Sparse values/indices')
                a=sparse.csr_matrix((data,idx,ptr),shape=shape)
                require(a.has_canonical_format,'Duplicate or unsorted sparse indices')
                matrices[name]=a
                hashes[name]=dict(shape=list(shape),data=logical(data),indices=logical(idx),indptr=logical(ptr))
            else:
                if h5py.check_string_dtype(obj.dtype):
                    arrays[name]=obj.asstr()[:]
                    from .identities import ordered_ids
                    hashes[name]=ordered_ids(arrays[name])
                else:arrays[name]=obj[:];hashes[name]=logical(arrays[name])
    return arrays,matrices,hashes


def validate_closed(folder,expected_spec_sha=None,*,final=True,allow_attempt=False,deep=True):
    folder=Path(folder);spec=read_json(folder/'run-spec.json')
    if final and not allow_attempt:require(not any(p.startswith('.attempt-') for p in folder.parts),'Attempt is not a promoted candidate')
    jsonschema.validate(spec,read_json(REPO/'schemas/mesh/phase0-spec.schema.json'))
    if expected_spec_sha:require(sha(folder/'run-spec.json')==expected_spec_sha,'Run specification changed')
    if final:
        manifest=read_json(folder/'manifest.json')
        jsonschema.validate(manifest,read_json(REPO/'schemas/mesh/phase0-manifest.schema.json'))
        require(manifest['run_spec_sha256']==sha(folder/'run-spec.json'),'Manifest specification identity')
        require(set(p.name for p in folder.iterdir())==set(manifest['files'])|{'manifest.json'},'Partial/extra candidate artifacts')
        for name,rec in manifest['files'].items():
            require(Path(name).name==name and file_record(folder/name)==rec,'File hash mismatch: '+name)
        if not deep:
            report=read_json(folder/'validation.json')
            require(report['status']=='pass','Validation did not pass')
            for name,rec in report['validated_files'].items():
                require(file_record(folder/name)==rec,'Payload changed since deep validation')
            require(report['validation_process']['status']=='pass','Deep validator process failed')
            return report
    arrays,matrices,hashes=load_payload(folder/'geometry.h5')
    require(set(arrays)==set(INTEGER_ARRAYS+FLOAT_ARRAYS+STRING_ARRAYS) and set(matrices)==set(MATRICES),'Payload dataset inventory')
    for name in INTEGER_ARRAYS:require(arrays[name].dtype==np.dtype('int64'),'Integer axis dtype: '+name)
    for name in FLOAT_ARRAYS:require(arrays[name].dtype==np.dtype('float64') and np.isfinite(arrays[name]).all(),'Float64 payload: '+name)
    if final:require(hashes==manifest['logical_hashes'],'Logical payload identity')
    v=arrays['vertices'];t=arrays['triangles'];triangles(v,t)
    require(np.array_equal(arrays['vertex_ids'],np.arange(len(v))),'Vertex identities')
    require(np.array_equal(arrays['active'],active(matrices['projector'])),'Algebraic active indices')
    require(np.array_equal(arrays['numerical_all'],(arrays['raw_all']-np.asarray(spec['transform']['origin']))/spec['transform']['scale']),'Coordinate transform corruption')
    require(logical(arrays['raw_all'])==spec['transform']['raw_hash'] and logical(arrays['numerical_all'])==spec['transform']['numerical_hash'],'Coordinate identity')
    idx=arrays['model_all_index'];require(np.array_equal(arrays['raw_model'],arrays['raw_all'][idx]),'Raw modeled coordinates')
    require(np.array_equal(arrays['numerical_model'],arrays['numerical_all'][idx]),'Modeled coordinate order')
    from .support import enclosure
    polygons=enclosure(arrays['numerical_all'],spec['collar'],spec['candidate']['buffer'],spec['config']['geometry']['offset_directions'])
    for name,expected in zip(['support','collar','outer'],polygons):
        require(np.array_equal(arrays[name],expected),'Enclosure does not match all-cell support: '+name)
    require(np.array_equal(arrays['model_rows'],arrays['all_rows'][idx]) and np.array_equal(arrays['model_ids'],arrays['all_ids'][idx]),'Modeled identity join')
    from .inputs import validate_population
    validate_population(dict(all_xy=arrays['raw_all'],model_xy=arrays['raw_model'],
        all_ids=arrays['all_ids'],model_ids=arrays['model_ids'],all_rows=arrays['all_rows'],
        model_rows=arrays['model_rows'],model_index=idx,types=arrays['model_types'],
        axis_order=np.array(['center_y','center_x'])),dict(all_cells=len(arrays['raw_all']),model_cells=len(idx)))
    projection=validate_projector(matrices['projector'],v,arrays['numerical_model'])
    independent=project(v,t,arrays['numerical_model']);delta=independent-matrices['projector']
    require(not delta.nnz or np.max(abs(delta.data))<1e-10,'Projector membership corruption')
    m,g=assemble(v,t)
    for name,expected in [('mass',m),('stiffness',g)]:
        delta=matrices[name]-expected
        require(not delta.nnz or np.max(abs(delta.data))<1e-12,'FEM matrix corruption')
    fem=validate_fem(v,t,m,g)
    u=arrays['eigenvectors'];lam=arrays['eigenvalues']
    require(u.shape==(len(v),len(v)) and lam.shape==(len(v),),'Incomplete spectrum')
    require(np.isfinite(u).all() and np.isfinite(lam).all() and np.all(lam>=0) and np.all(np.diff(lam)>=0),'Invalid eigenvalues/vectors')
    require(np.max(abs(u.T@(m@u)-np.eye(len(v))))<1e-9,'Eigenvector mass orthogonality')
    require(np.linalg.norm(g@u-(m@u)*lam)/max(np.linalg.norm(g@u),1)<1e-9,'Eigenpair residual')
    regions,geometry=diagnostics(v,t,arrays['support'],arrays['collar'],arrays['outer'],spec['candidate']['h'],spec['edge_cap'])
    require(np.array_equal(regions,arrays['regions']),'Region-label corruption')
    require(geometry['max_edge_target_ratio']<=1+spec['config']['geometry']['grading_relative_tolerance'],'Grading violation')
    probes=read_json(folder/'probes.json');require(len(probes['indices'])==256 and len(set(probes['indices']))==256,'Fixed probe set incomplete')
    require(arrays['model_rows'][probes['indices']].tolist()==probes['source_rows'],'Probe identity corruption')
    from .probes import choose
    _,expected_probes=choose(arrays['numerical_model'],arrays['model_rows'],arrays['support'],spec['config']['probes'])
    require(expected_probes==probes and probes['identities_sha256']==spec['probe_identities_sha256'],'Probe rule/identity corruption')
    results=read_json(folder/'ranges.json')
    require([(r['range_id'],r['ell'],r['role']) for r in results]==[(r['range_id'],r['ell'],r['role']) for r in spec['ranges']],'Missing/substituted ranges')
    require(read_json(folder/'compute.json')['spectrum']['modes']==len(v),'Spectrum truncation')
    require(read_json(folder/'execution.json')['status']=='pass','Worker execution did not pass')
    if final:require(read_json(folder/'validation.json')['status']=='pass','Validation status')
    return dict(status='pass',scope='experimental_phase0_not_production_mesh',logical_hashes=hashes,projection=projection,fem=fem,geometry=geometry,
        validated_files={name:file_record(folder/name) for name in ['run-spec.json','geometry.h5','probes.json','ranges.json','compute.json','execution.json']})


def finalize(attempt,destination,expected_spec_sha,*,validated_report=None):
    attempt=Path(attempt);destination=Path(destination)
    require(not destination.exists(),'Refusing finalized overwrite')
    report=validate_closed(attempt,expected_spec_sha,final=False) if validated_report is None else validated_report
    require(report['status']=='pass' and sha(attempt/'run-spec.json')==expected_spec_sha,'Validated specification changed')
    for name,rec in report['validated_files'].items():require(file_record(attempt/name)==rec,'Payload changed after validation')
    for path in attempt.iterdir():
        if path.is_file():
            with path.open('r+b') as stream:stream.flush();os.fsync(stream.fileno())
    write_json(attempt/'validation.json',report)
    files={p.name:file_record(p) for p in sorted(attempt.iterdir()) if p.is_file()}
    require(all(p.is_file() for p in attempt.iterdir()),'Unregistered attempt subdirectory')
    write_json(attempt/'manifest.json',dict(schema='bsfm.mesh.phase0.candidate.v1',status='complete',experimental=True,
        run_spec_sha256=expected_spec_sha,files=files,logical_hashes=report['logical_hashes']))
    validate_closed(attempt,expected_spec_sha,allow_attempt=True,deep=validated_report is None)
    require(attempt.stat().st_dev==destination.parent.stat().st_dev,'Cross-filesystem promotion forbidden')
    os.rename(attempt,destination)
    return destination
