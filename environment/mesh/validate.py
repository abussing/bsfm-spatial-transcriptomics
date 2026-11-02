"""Independent tiny cross-language environment checks; never a Phase-0 run."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

import h5py
import jsonschema
import numpy as np
import psutil
import scipy
import scipy.io
import scipy.linalg
import scipy.spatial
import scipy.special


def digest(data):return hashlib.sha256(data).hexdigest()


def payload(array,dtype):return digest(np.asarray(array,dtype=dtype).tobytes(order='C'))


def read_run(folder):
    meta=json.loads((folder/'result.json').read_text(encoding='utf-8'));assert meta['status']=='pass'
    assert meta['triangle_index_base']==0 and meta['r_internal_triangle_index_base']==1
    n=meta['vertices']; nt=meta['triangles']; nq=meta['queries']
    v=np.fromfile(folder/'vertices.f64',dtype='<f8').reshape(n,2)
    t=np.fromfile(folder/'triangles.i32',dtype='<i4').reshape(nt,3)
    q=np.fromfile(folder/'queries.f64',dtype='<f8').reshape(nq,2)
    dense=np.fromfile(folder/'projector.f64',dtype='<f8').reshape(nq,n)
    a=scipy.io.mmread(folder/'projector.mtx',spmatrix=True).tocsr()
    assert t.min()==0 and t.max()<n and np.unique(t).size==n
    assert np.array_equal(v[0],q[0])
    assert np.allclose(q[1],v[t[0,:2]].mean(axis=0),atol=1e-15,rtol=0)
    assert np.allclose(q[2],v[t[0]].mean(axis=0),atol=1e-15,rtol=0)
    rowerr=float(np.max(abs(np.asarray(a.sum(axis=1)).ravel()-1)))
    affine=float(np.max(abs(a@v-q)));mm=float(np.max(abs(a.toarray()-dense)))
    assert rowerr<1e-12 and affine<1e-12 and mm<1e-15
    def validate_indices(x,base):
        if base!=0 or x.min()!=0 or x.max()>=n:raise ValueError('Expected complete zero-based mesh indexing')
    failures=0
    for bad,base in [(t+1,0),(t,1)]:
        try:validate_indices(bad,base)
        except ValueError:failures+=1
    assert failures==2
    scipy.io.mmwrite(folder/'python-projector.mtx',a,precision=17)
    # Test an actual HDF5 round trip only with these tiny synthetic arrays.
    with h5py.File(folder/'python-roundtrip.h5','w') as f:
        for name,data in [('vertices',v),('triangles',t),('queries',q),('projector',dense)]:f[name]=data
    with h5py.File(folder/'python-roundtrip.h5','r') as f:
        for name,data in [('vertices',v),('triangles',t),('queries',q),('projector',dense)]:assert np.array_equal(f[name][...],data)
    return dict(vertices=n,triangles=nt,projector_shape=list(a.shape),projector_nnz=a.nnz,
        row_sum_error=rowerr,affine_error=affine,matrix_market_error=mm,
        rejected_index_corruptions=failures,semantic_hashes=dict(vertices=payload(v,'<f8'),
        triangles=payload(t,'<i4'),queries=payload(q,'<f8'),projector=payload(dense,'<f8')))


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path);ap.add_argument('--run-root',required=True,type=Path)
    ap.add_argument('--validation-name',default='validation')
    args=ap.parse_args();root=args.root.resolve();repo=Path(__file__).resolve().parents[2]
    assert re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*',args.validation_name)
    validation=root/args.validation_name
    assert Path(sys.prefix).resolve()==root/'python',sys.prefix
    lock=json.loads((root/'r-source-lock.json').read_text(encoding='utf-8'));rs=lock['runtime']['path']
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',LANG='C',LC_ALL='C',TMP=str(root/'tmp'),TEMP=str(root/'tmp'),TMPDIR=str(root/'tmp'))
    commands=[];rlogs=[]
    for i in [1,2]:
        dest=validation/f'fresh-{i}';command=[rs,'--vanilla',str(Path(__file__).with_suffix('.R')),str(root),str(dest)]
        process=subprocess.run(command,env=env,capture_output=True,text=True)
        log=process.stdout+process.stderr
        (validation/f'process-{i}.log').write_text(log,encoding='utf-8')
        assert process.returncode==0,log
        assert 'stack imbalance' not in log.lower(),log
        commands.append(command);rlogs.append(log)
    records=[read_run(validation/f'fresh-{i}') for i in [1,2]]
    assert records[0]['semantic_hashes']==records[1]['semantic_hashes']
    reverse_command=[rs,'--vanilla',str(Path(__file__).with_name('roundtrip.R')),str(root),str(validation)]
    reverse=subprocess.run(reverse_command,env=env,capture_output=True,text=True)
    (validation/'reverse-process.log').write_text(reverse.stdout+reverse.stderr,encoding='utf-8')
    assert reverse.returncode==0,reverse.stdout+reverse.stderr
    assert 'stack imbalance' not in (reverse.stdout+reverse.stderr).lower()
    # Only two canonical JSON metadata files are opened; never response arrays.
    rm=(args.run_root/'run-manifest.json').read_bytes()
    assert digest(rm)=='03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f'
    manifest=json.loads(rm);assert manifest['status']=='complete' and manifest['pass']
    registry=repo/'src/bsfm/preprocessing/sections.json';rb=registry.read_bytes()
    assert digest(rb)==manifest['identities']['section_registry_sha256']
    assert manifest['section_order']==[x['section'] for x in json.loads(rb)['sections']]
    jsonschema.validate({'kind':'synthetic'},{'type':'object','required':['kind']})
    # Independent reference: known congruence gives exact eigenvalues [1,4,9].
    m=np.diag([2.,3.,5.]);g=np.diag([2.,12.,45.]);w,u=scipy.linalg.eigh(g,m)
    eig=float(np.max(abs(w-np.array([1.,4.,9.]))));orth=float(np.max(abs(u.T@m@u-np.eye(3))))
    residual=float(np.max(abs(g@u-(m@u)*w)));assert max(eig,orth,residual)<1e-12
    z=np.array([1e-8,.1,1.,10.]);vals=scipy.special.kv(5,z)
    assert np.isfinite(vals).all() and (vals>0).all()
    # Half-order Bessel K has an independent elementary formula.
    half=scipy.special.kv(.5,z);expected=np.sqrt(np.pi/(2*z))*np.exp(-z)
    bessel=float(np.max(abs(half/expected-1)));assert bessel<1e-14
    # Process-tree measurement includes an actual live child.
    child=subprocess.Popen([sys.executable,'-B','-c','import sys; print("ready",flush=True); sys.stdin.read()'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,text=True)
    try:
        assert child.stdout.readline().strip()=='ready'
        parent=psutil.Process();tree=[parent]+parent.children(recursive=True)
        assert child.pid in [p.pid for p in tree]
        rss=sum(p.memory_info().rss for p in tree);assert rss>0
    finally:child.communicate('close',timeout=10)
    config=dict(numpy=np.show_config(mode='dicts'),scipy=scipy.show_config(mode='dicts'))
    (root/'python-numerical-config.json').write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    result=dict(schema_version=1,status='pass',scope='environment validation only; no real mesh',
        python=sys.version,executable=sys.executable,base_executable=sys._base_executable,
        platform=platform.platform(),packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','h5py','psutil','jsonschema']},
        hdf5=h5py.version.hdf5_version,r_commands=commands,reverse_command=reverse_command,r_runs=records,
        deterministic_semantics=True,coordinate_order='coordinate_0, coordinate_1; no swap',
        metadata_authentication=dict(run_manifest=digest(rm),section_registry=digest(rb)),
        generalized_eigenvalue_error=eig,orthogonality_error=orth,eigen_residual=residual,
        bessel_half_order_relative_error=bessel,bessel_order5_values=vals.tolist(),
        process_tree=dict(processes=len(tree),rss_bytes=rss,child_detected=True),
        hdf5_roundtrip='exact',python_to_r_matrix_market='exact',stack_imbalance_detected=False)
    (root/'validation-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
