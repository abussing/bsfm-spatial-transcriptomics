"""Bounded S10 fixed-W/joint-eta mechanical smoke; synthetic G/K, no fit/sweep."""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

import jax
import numpy as np
from scipy.special import logit
from threadpoolctl import threadpool_limits
from bsfm.mesh.identities import logical
from bsfm.sampler import contracts, warp
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.layer4 import CenteredHyperTarget, JointEtaConditional, state_hashes
from bsfm.sampler.rule import load_rule
from audit_sampler_layer3_s10 import sha, peak_working_set

ROOT=Path(__file__).resolve().parents[1]


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mesh-artifact',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    a=p.parse_args();start=time.perf_counter()
    receipt=ROOT/'docs/mesh/audits/october26_S10_localization_20261102/corrected-reproduction.json'
    approved=json.loads(receipt.read_text())
    assert a.mesh_artifact.stat().st_size==approved['output']['bytes']
    assert sha(a.mesh_artifact)==approved['output']['sha256']
    keys=['mesh_vertices','A_full','slocs','source_rows','cell_type','active_indices_full',
          'fem_C',*[f'fem_g{j}' for j in range(1,7)]]
    with np.load(a.mesh_artifact,allow_pickle=False) as f:data={k:f[k] for k in keys}
    for k,v in data.items():assert logical(v)==approved['arrays'][k]['sha256'],k
    n=len(data['slocs']);rows=data['source_rows'];idx=data['active_indices_full']
    mesh=dict(terms=np.stack([data['fem_C']]+[data[f'fem_g{j}'] for j in range(1,7)]),
        vertices=data['mesh_vertices'],projector=data['A_full'],locations=data['slocs'],
        active_indices=idx,vertex_ids=np.array([f'vertex-row:{i}' for i in range(len(data['mesh_vertices']))]),
        cell_ids=np.array([f'raw-source-row:{i}' for i in rows]),source_rows=rows)
    with threadpool_limits(limits=1):
        geometry=warp.WarpGeometry.authenticate(mesh,warp.mesh_identity(mesh,section='S10__WT5',mesh_sha256=approved['output']['sha256']))
        rng=np.random.default_rng(410)
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
        ps=tuple(target.position(fid,log_alpha=np.log(state.alpha[k]),logit_zeta=logit(state.zeta[k]),
            log_ell=0.,log_r=np.log(.8),zW=rng.normal(0,.1,(len(idx),2))) for k,fid in enumerate(ids))
        centered=CenteredHyperTarget(target);joint=JointEtaConditional(target)
        before=state_hashes(state);runs=[];outputs=[]
        for _ in range(2):
            begin=time.perf_counter();field=centered.freeze(ps[0],state,state_factor_ids=ids)
            value,grad,context=centered.value_grad(ps[0].values[2:4],field,state,state_factor_ids=ids)
            z,rewhite=centered.rewhiten(ps[0].values[2:4]+np.array([.02,-.01]),field,state,state_factor_ids=ids)
            center_seconds=time.perf_counter()-begin;begin=time.perf_counter()
            eta,beta,diag,record=joint.draw(ps,state,np.random.default_rng(411),state_factor_ids=ids)
            draw_seconds=time.perf_counter()-begin
            hashes={name:contracts.logical_hash(v) for name,v in dict(eta=eta,beta=beta,gradient=grad,rewhitened=z,W_active=field.values).items()}
            outputs.append(dict(value=value,diagnostics=asdict(diag),hashes=hashes,record=record,rewhitening=rewhite))
            runs.append(dict(centered_seconds=center_seconds,joint_eta_seconds=draw_seconds,diagnostics=asdict(diag)))
        assert outputs[0]==outputs[1]
        assert before==state_hashes(state)
    assert sha(a.mesh_artifact)==approved['output']['sha256']
    report=dict(schema='bsfm.sampler-layer4-S10-smoke.v1',status='PASS',review_status='proposed_for_review',
        scope='Synthetic two-gene/two-factor numerical smoke on existing geometry; no mixing test, scientific fit, K selection or mesh rebuild',
        baseline_commit='7d18eaeade6046367cb65588a98ab99199cf8108',
        artifact=dict(path_machine_local=str(a.mesh_artifact),**approved['output']),
        identity_limitation='Cell IDs explicitly alias raw source rows, not unavailable original cell-name strings; Y and GaussianState are synthetic',
        cells=n,types=np.bincount(data['cell_type'],minlength=3).tolist(),genes=2,synthetic_factors=2,
        full_vertices=len(mesh['vertices']),full_modes=geometry.spectral['U'].shape[1],active_vertices=len(idx),
        feature_shape=[2,n,1024],eta_shape=list(eta.shape),beta_shape=list(beta.shape),
        fixed_W_value=value,fixed_W_gradient=grad.tolist(),exact_repeat=True,state_unchanged=True,
        rewhitening=rewhite,logical_hashes=outputs[0]['hashes'],runs=runs,total_seconds=time.perf_counter()-start,
        peak_process_working_set_bytes=peak_working_set(),
        memory_measurement='Windows process lifetime peak resident working set including Python/JAX/native libraries; no child workers',
        executable=sys.executable,backend=jax.default_backend(),x64=jax.config.x64_enabled,
        synthetic_seed=410,draw_seed=411,target_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),
        code_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__).resolve(),*sorted((ROOT/'src/bsfm/sampler').glob('*.py'))]})
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:report[k] for k in ['status','cells','full_modes','active_vertices','feature_shape','runs','exact_repeat','rewhitening','total_seconds','peak_process_working_set_bytes']},indent=2))


if __name__=='__main__':main()
