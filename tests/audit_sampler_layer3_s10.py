"""One S10 mechanical target evaluation; synthetic Y/state, no fitting or sweep."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sys
import time
import jax
import numpy as np
from threadpoolctl import threadpool_limits
from bsfm.mesh.identities import logical
from bsfm.sampler import contracts, warp
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.rule import load_rule

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def peak_working_set():
    """Windows process high-water mark; includes Python/JAX, no child workers used."""
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
            (x,ctypes.c_size_t) for x in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage')]
    get_current=ctypes.windll.kernel32.GetCurrentProcess
    get_current.restype=wintypes.HANDLE
    query=ctypes.windll.psapi.GetProcessMemoryInfo
    query.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    result=Counters();result.cb=ctypes.sizeof(result)
    if not query(get_current(),ctypes.byref(result),result.cb):raise ctypes.WinError()
    return int(result.PeakWorkingSetSize)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh-artifact',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();start=time.perf_counter()
    receipt=ROOT/'docs/mesh/audits/october26_S10_localization_20261102/corrected-reproduction.json'
    approved=json.loads(receipt.read_text(encoding='utf-8'))
    assert args.mesh_artifact.stat().st_size==approved['output']['bytes']
    assert sha(args.mesh_artifact)==approved['output']['sha256']
    keys=['mesh_vertices','A_full','slocs','source_rows','cell_type','active_indices_full',
          'fem_C',*[f'fem_g{j}' for j in range(1,7)]]
    with np.load(args.mesh_artifact,allow_pickle=False) as f:data={k:f[k] for k in keys}
    for k,v in data.items():assert logical(v)==approved['arrays'][k]['sha256'],k
    n=len(data['slocs']);rows=data['source_rows'];idx=data['active_indices_full']
    mesh=dict(terms=np.stack([data['fem_C']]+[data[f'fem_g{j}'] for j in range(1,7)]),
        vertices=data['mesh_vertices'],projector=data['A_full'],locations=data['slocs'],
        active_indices=idx,vertex_ids=np.array([f'vertex-row:{i}' for i in range(len(data['mesh_vertices']))]),
        cell_ids=np.array([f'raw-source-row:{i}' for i in rows]),source_rows=rows)
    with threadpool_limits(limits=1):
        geometry=warp.WarpGeometry.authenticate(mesh,warp.mesh_identity(mesh,section='S10__WT5',mesh_sha256=approved['output']['sha256']))
        rng=np.random.default_rng(310)
        raw=dict(Y=rng.normal(0,.1,(2,n)),slocs=mesh['locations'],cell_id=data['cell_type'],
            cell_names=mesh['cell_ids'],source_row_indices=rows,
            gene_names=np.array(['synthetic-gene-a','synthetic-gene-b']),cell_type_names=np.array(['MIC','AST','OGC']))
        identity=contracts.input_identity(raw,section='S10__WT5',response_sha256=contracts.logical_hash(raw['Y']),coordinate_system='october26_glial_min_max_span')
        inputs=contracts.ModelInput.authenticate(raw,identity)
        state=contracts.GaussianState(rng.normal(0,.2,(3,2,2)),rng.normal(0,.1,(2,n)),
            np.array([.7,.8]),np.array([.4,.6]),np.array([.8,1.1]),np.full((2,2),1.1),
            np.array([1.1,.8]),np.cumprod(np.array([1.1,.8])),inputs.identity_json)
        ids=('synthetic-factor-a','synthetic-factor-b')
        target=DirectWTarget(inputs,geometry,load_rule(),factor_ids=ids)
        pos=target.position(ids[0],log_alpha=np.log(.7),logit_zeta=0.,log_ell=0.,log_r=np.log(.8),zW=rng.normal(0,.1,(len(idx),2)))
        begin=time.perf_counter();value,grad,context=target.value_grad(pos,state,state_factor_ids=ids)
        first_seconds=time.perf_counter()-begin
        begin=time.perf_counter();other,grad2,context2=target.value_grad(pos,state,state_factor_ids=ids)
        repeat_seconds=time.perf_counter()-begin
        assert value==other and np.array_equal(grad,grad2) and context==context2
        w,wa,features=target.features(pos)
        assert features.shape==(n,1024) and np.isfinite(features).all()
        assert len(geometry.spectral['U'])==371
    assert sha(args.mesh_artifact)==approved['output']['sha256']
    report=dict(schema='bsfm.sampler-layer3-S10-smoke.v1',status='PASS',
        scope='One mechanical target, synthetic two-gene/two-factor state; not K selection, fit, mixing or scientific accuracy evidence',
        baseline='d76927b274bfca9e9e24032ee7db07241fbb6d00',
        artifact=dict(path_machine_local=str(args.mesh_artifact),**approved['output']),
        mesh_receipt_sha256=sha(receipt),input_identity=identity,
        identity_limitation='Raw source-row aliases, not original cell-name strings; synthetic response hash is not an expression-source fingerprint',
        cells=n,types=np.bincount(data['cell_type'],minlength=3).tolist(),genes=2,synthetic_factors=2,
        full_vertices=371,full_modes=geometry.spectral['U'].shape[1],active_vertices=len(idx),
        feature_shape=list(features.shape),position_shape=list(pos.values.shape),gradient_shape=list(grad.shape),
        value=value,gradient_finite=bool(np.isfinite(grad).all()),gradient_norm=float(np.linalg.norm(grad)),
        exact_repeat=True,logical_hashes={k:contracts.logical_hash(v) for k,v in dict(gradient=grad,W=w,W_active=wa,features=features).items()},
        target_identity_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),
        context=context,first_value_gradient_seconds=first_seconds,repeat_value_gradient_seconds=repeat_seconds,
        total_seconds=time.perf_counter()-start,peak_process_working_set_bytes=peak_working_set(),
        memory_measurement='Windows GetProcessMemoryInfo lifetime peak resident working set, Python/JAX/native libraries included; no subprocess workers in smoke',
        executable=sys.executable,backend=jax.default_backend(),x64=jax.config.x64_enabled,
        seed=310,ell_W=1.,r_W=.8,ell_eta=.14,
        code_sha256={str(q.relative_to(ROOT)).replace('\\','/'):sha(q) for q in [Path(__file__).resolve(),*sorted((ROOT/'src/bsfm/sampler').glob('*.py'))]})
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ('status','cells','full_modes','active_vertices','feature_shape','value','exact_repeat','total_seconds','peak_process_working_set_bytes')},indent=2))


if __name__=='__main__':main()
