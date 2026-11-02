"""One authenticated S10 geometry-only audit; no expression, rebuild or sampler."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import jax
import numpy as np
from threadpoolctl import threadpool_limits

from bsfm.mesh.identities import logical
from bsfm.mesh.october26 import marginal_root, relative as mesh_relative
from bsfm.sampler import warp
from sampler_layer2_support import ROOT, historical_reference, evaluate, port_functions, relative


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def compare(a,b):
    if isinstance(a,dict):
        assert a.keys()==b.keys()
        return {k:compare(a[k],b[k]) for k in a}
    if isinstance(a,(np.ndarray,jax.Array)):
        x,y=np.asarray(a),np.asarray(b)
        return dict(exact=bool(np.array_equal(x,y)),max_absolute_difference=float(np.max(np.abs(x-y))),
                    relative_frobenius=relative(x,y),shape=list(x.shape),logical_sha256=logical(x))
    assert a==b,(a,b)
    return dict(exact=True)


def all_exact(comparison):
    if 'exact' in comparison:return comparison['exact']
    return all(all_exact(x) for x in comparison.values())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mesh-artifact',required=True,type=Path)
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();start=time.perf_counter()
    report_path=ROOT/'docs/mesh/audits/october26_S10_localization_20261102/corrected-reproduction.json'
    approved=json.loads(report_path.read_text(encoding='utf-8'))
    assert args.mesh_artifact.stat().st_size==approved['output']['bytes']
    assert sha(args.mesh_artifact)==approved['output']['sha256']
    reference,sources=historical_reference(args.source_root)
    with np.load(args.mesh_artifact,allow_pickle=False) as archive:
        arrays={k:archive[k] for k in ['mesh_vertices','A_full','slocs','source_rows',
                'active_indices_full','historical_half_rows','historical_half_active',
                'historical_half_A_active','modal_diagonals','spectral_U',
                'fem_C',*[f'fem_g{j}' for j in range(1,7)]]}
    for name,a in arrays.items():assert logical(a)==approved['arrays'][name]['sha256'],name
    results=[]
    with threadpool_limits(limits=1):
        for population in ['full_geometry_cells','historical_retained_cells']:
            keep=np.arange(len(arrays['slocs'])) if population=='full_geometry_cells' else arrays['historical_half_rows']
            idx=arrays['active_indices_full'] if population=='full_geometry_cells' else arrays['historical_half_active']
            source_rows=arrays['source_rows'][keep]
            data=dict(terms=np.stack([arrays['fem_C']]+[arrays[f'fem_g{j}'] for j in range(1,7)]),
                      vertices=arrays['mesh_vertices'],projector=arrays['A_full'][keep],
                      locations=arrays['slocs'][keep],active_indices=idx,
                      vertex_ids=np.array([f'vertex-row:{i}' for i in range(len(arrays['mesh_vertices']))]),
                      cell_ids=np.array([f'raw-source-row:{i}' for i in source_rows]),source_rows=source_rows)
            identity=warp.mesh_identity(data,section='S10__WT5',mesh_sha256=approved['output']['sha256'])
            geometry=warp.WarpGeometry.authenticate(data,identity)
            x=0. # ell=1: existing canonical mechanical-check range, not a range study.
            before=time.perf_counter()
            historical=evaluate(reference,data,x);port=evaluate(port_functions(),data,x)
            comparison=compare(port,historical)
            assert all_exact(comparison),'Source/port mismatch; report before changing any tolerance'
            repeat=compare(port,evaluate(port_functions(),data,x))
            assert all_exact(repeat),'Nondeterministic repeat'
            l,lr,cov,covr,geo=geometry.geometry(x)
            u=geometry.spectral['U'];sd=np.asarray(geo['modal_sd'])
            full=(u*sd)@(u*sd).T
            marginal_error=relative(cov,full[np.ix_(idx,idx)])
            root_error=relative(l@l.T,cov);derivative_error=relative(lr@l.T+l@lr.T,covr)
            projected_factor_error=relative(data['projector']@u,(data['projector'][:,idx]@u[idx]))
            canonical_root,canonical_sd=marginal_root(u,geometry.spectral['modal_diagonals'],idx,1.)
            root_reuse_error=relative(l,canonical_root);sd_reuse_error=relative(sd,canonical_sd)
            z=np.arange(len(idx)*2,dtype=float).reshape(-1,2)/(len(idx)*2)-.5
            physical=geometry.physical(x,np.log(.8),z)
            newz,rewhite=geometry.rewhiten(np.asarray(physical['W_active']),np.log(.9),np.log(.7))
            restored=geometry.physical(np.log(.9),np.log(.7),newz)
            cells_error=float(np.max(np.abs(np.asarray(restored['W_cell'])-np.asarray(physical['W_cell']))))
            metrics=dict(full_to_active_covariance_relative=marginal_error,root_reconstruction_relative=root_error,
                         root_derivative_identity_relative=derivative_error,full_to_active_projected_modes_relative=projected_factor_error,
                         canonical_numpy_root_relative=root_reuse_error,canonical_numpy_modal_sd_relative=sd_reuse_error,
                         projector_row_sum_max=float(np.max(abs(data['projector'].sum(1)-1))),
                         projector_affine_max=float(np.max(abs(data['projector']@data['vertices']-data['locations']))),
                         rewhiten_active_max=rewhite['max_absolute_error'],rewhiten_cell_max=cells_error)
            assert max(marginal_error,root_error,derivative_error,projected_factor_error,root_reuse_error,sd_reuse_error)<2e-10
            assert metrics['projector_row_sum_max']<=5e-12 and metrics['projector_affine_max']<=5e-12*max(1.,abs(data['vertices']).max())
            assert max(rewhite['max_absolute_error'],cells_error)<=2e-8
            assert float(geo['log_amplitude_scale'])==0. and np.all(sd>0) and np.all(np.diag(l)>0)
            results.append(dict(population=population,cells=len(keep),vertices=len(u),active_vertices=len(idx),
                                full_modes=u.shape[1],ell=1.,exact_reference=True,exact_repeat=True,
                                identity=identity,spectral_audit=dict(geometry.spectral['audit']),metrics=metrics,
                                historical_comparison=comparison,seconds=time.perf_counter()-before))
    assert sha(args.mesh_artifact)==approved['output']['sha256']
    report=dict(schema='bsfm.sampler-layer2-S10-audit.v1',status='PASS',
                scope='deterministic geometry and warp foundation only; no sampler or mesh rebuild',
                artifact=dict(path_machine_local=str(args.mesh_artifact),**approved['output']),
                source_files=sources,populations=results,seconds=time.perf_counter()-start,
                dense_inverse_scope='Synthetic tests use independent dense precision inverse and Schur complement. S10 compares all-mode dense full covariance with its active submatrix, without claiming a numerically reliable inverse of ill-conditioned raw S10 precision.',
                identity_note='Cell identifiers in this audit explicitly name authenticated raw source rows; original cell-name strings are not supplied by the mesh artifact. No cell order is inferred from section suffix.',
                platform_scope='Same authenticated sources in one pinned Windows CPU environment, not historical Linux byte equivalence.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(status='PASS',seconds=report['seconds'],populations=[dict(population=x['population'],cells=x['cells'],vertices=x['vertices'],active=x['active_vertices'],metrics=x['metrics']) for x in results]),indent=2))


if __name__=='__main__':main()
