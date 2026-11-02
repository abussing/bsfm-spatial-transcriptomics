"""Sequential experimental pilot; real execution requires explicit clean-commit command."""
import argparse
import os
from pathlib import Path
import sys
import time
import traceback
import numpy as np
import jsonschema
from .identities import REPO,read_json,write_json,require,sha,logical,file_record
from .inputs import real_inputs,environment,code
from .coordinates import transform
from .support import hull
from .probes import choose
from .bridge import build
from .fem import assemble,validate as validate_fem
from .spectral import spectrum
from .projectors import active
from .accuracy import evaluate
from .resources import supervised,preflight,GiB
from .artifacts import new_attempt,save_payload,finalize,validate_closed


def candidates(study):
    return [dict(id=f"{h['level']}-g0-{b['level']}",h=h['value'],buffer=b['value'])
        for h in study['factors']['inner_targets'] for b in study['factors']['buffers']]


def validate_design(study,config):
    """Reject a changed scientific contract that the implementation cannot honor."""
    from .coordinates import SCALE
    require(study['target']['nu']==5 and study['target']['amplitude']==1 and study['target']['kappa']=='sqrt(40)/ell','Unsupported covariance target')
    require(study['coordinates']['scale']==SCALE and study['coordinates']['axis_order']==['center_y','center_x'] and study['coordinates']['units']=='source_native','Coordinate design mismatch')
    require(study['factors']['grading'][0]['formula']=='min(h_inner+0.15*d,ell_high/4)','Unsupported grading')
    require(config['resources']['concurrency']==1 and config['resources']['minimum_available_GiB']==8 and config['resources']['process_tree_ceiling_GiB']==10,'Resource contract mismatch')
    require(config['probes']['count_per_stratum']==64 and config['probes']['density_neighbors']==20,'Probe contract mismatch')
    require(len(candidates(study))==6 and len(study['factors']['ranges'])==23,'Incomplete real candidate/range grid')


def worker(spec_path,input_path,bundle,work):
    spec=read_json(spec_path);bundle=Path(bundle);work=Path(work)
    jsonschema.validate(spec,read_json(REPO/'schemas/mesh/phase0-spec.schema.json'))
    require(file_record(input_path)==spec['input_transport'],'Input transport changed')
    with np.load(input_path,allow_pickle=False) as f:data={k:f[k] for k in f.files}
    num,trans=transform(data['all_xy']);require(trans==spec['transform'],'Worker coordinate identity')
    model=num[data['model_index']]
    start=time.perf_counter()
    geo=build(num,model,Path(spec['environment_root']),work/'bridge',spec['candidate']['h'],spec['collar'],spec['candidate']['buffer'],spec['edge_cap'],spec['config']['geometry'])
    mesh_seconds=time.perf_counter()-start
    v=geo['vertices'];t=geo['triangles'];a=geo['projector'];indices=active(a)
    estimate=8*(8*len(v)**2+8*len(indices)**2+4*len(v)*len(indices))
    require(estimate<spec['config']['resources']['process_tree_ceiling_GiB']*GiB,'Resource exclusion: dense algebra estimate exceeds ceiling; no spectrum reduction')
    m,g=assemble(v,t);fem=validate_fem(v,t,m,g)
    started=time.perf_counter();lam,u,eigen=spectrum(m,g);eigen_seconds=time.perf_counter()-started
    probes=read_json(bundle/'probes.json');idx=np.array(probes['indices'])
    result=evaluate(u,lam,indices,a,model,idx,probes,spec['ranges'],spec['config']['numerics'])
    arrays=dict(vertices=v,vertex_ids=np.arange(len(v),dtype='int64'),triangles=t.astype('int64'),regions=geo['regions'],active=indices,
        support=geo['support'],collar=geo['collar'],outer=geo['outer'],eigenvalues=lam,eigenvectors=u,
        raw_all=data['all_xy'],raw_model=data['model_xy'],numerical_all=num,numerical_model=model,
        all_ids=data['all_ids'],model_ids=data['model_ids'],all_rows=data['all_rows'],model_rows=data['model_rows'],model_all_index=data['model_index'],model_types=data['types'])
    save_payload(bundle/'geometry.h5',arrays,dict(projector=a,mass=m,stiffness=g))
    write_json(bundle/'ranges.json',result)
    write_json(bundle/'compute.json',dict(status='pass',experimental=True,geometry=geo['geometry'],fem=fem,spectrum=eigen,
        dimensions=dict(all_cells=len(num),model_cells=len(model),vertices=len(v),active=len(indices)),
        timing=dict(mesh_seconds=mesh_seconds,eigensolve_seconds=eigen_seconds,total_worker_seconds=time.perf_counter()-start),
        dense_algebra_estimate_bytes=estimate,projected_sampler_cost=dict(dense_active_factorization_cubic=int(len(indices)**3)),
        continuous_interval_certified=False,accuracy_thresholds_selected=False))


def run(data,provenance,envroot,root,study,config,*,synthetic=False,selected_candidates=None):
    root=Path(root);require(not root.exists(),'Fresh study root required; existing attempts are never silently resumed')
    root.mkdir(parents=True)
    np.savez(root/'inputs.npz',**data)
    numerical,trans=transform(data['all_xy'])
    idx,probes=choose(numerical[data['model_index']],data['model_rows'],hull(numerical),config['probes'])
    write_json(root/'probes.json',probes)
    chosen=candidates(study) if selected_candidates is None else selected_candidates
    if not synthetic:require(chosen==candidates(study) and len(chosen)==6,'Real pilot must retain all six candidates')
    ledger=[];write_json(root/'run-spec.json',dict(schema='bsfm.mesh.phase0.study.v1',experimental=True,synthetic=synthetic,
        provenance=provenance,study=study,config=config,input_transport=file_record(root/'inputs.npz'),probes_sha256=sha(root/'probes.json'),candidates=chosen))
    for candidate in chosen:
        attempt=new_attempt(root,candidate['id']);bundle=attempt/'bundle';bundle.mkdir();work=attempt/'work';work.mkdir()
        spec=dict(schema='bsfm.mesh.phase0.spec.v1',experimental=True,synthetic=synthetic,candidate=candidate,
            provenance=provenance,environment_root=str(Path(envroot).resolve()),config=config,
            input_transport=file_record(root/'inputs.npz'),transform=trans,collar=study['factors']['fine_collar'],
            edge_cap=study['accuracy']['central99'][1]/4,
            ranges=study['factors']['ranges'],probe_identities_sha256=probes['identities_sha256'])
        write_json(bundle/'run-spec.json',spec);write_json(bundle/'probes.json',probes)
        jsonschema.validate(spec,read_json(REPO/'schemas/mesh/phase0-spec.schema.json'))
        expected=sha(bundle/'run-spec.json')
        env=os.environ.copy();env.update(PYTHONPATH=str(REPO/'src'),OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        command=[str(Path(envroot)/'python/Scripts/python.exe'),'-B','-m','bsfm.mesh.phase0','--worker',str(bundle/'run-spec.json'),str(root/'inputs.npz'),str(bundle),str(work)]
        try:
            if not synthetic:
                require(code(provenance['code']['commit'],real=True)==provenance['code'],'Code identity changed between candidates')
                require(sha(REPO/'config/mesh/study-design.json')==provenance['study_sha256'] and sha(REPO/'config/mesh/phase0-harness.json')==provenance['harness_config_sha256'],'Configuration changed')
            resources=supervised(command,REPO,env,attempt/'worker.log',bundle/'execution.json',
                ceiling_GiB=config['resources']['process_tree_ceiling_GiB'],minimum_GiB=0 if synthetic else config['resources']['minimum_available_GiB'],poll_seconds=config['resources']['poll_seconds'])
            validation_command=[command[0],'-B','-m','bsfm.mesh.phase0','--validate-worker',str(bundle),expected,str(attempt/'deep-validation.json')]
            validation_process=supervised(validation_command,REPO,env,attempt/'validator.log',attempt/'validator-execution.json',
                ceiling_GiB=config['resources']['process_tree_ceiling_GiB'],minimum_GiB=0 if synthetic else config['resources']['minimum_available_GiB'],poll_seconds=config['resources']['poll_seconds'])
            report=read_json(attempt/'deep-validation.json');report['validation_process']=validation_process
            dest=finalize(bundle,root/candidate['id'],expected,validated_report=report)
            ledger.append(dict(candidate=candidate['id'],status='pass',manifest=file_record(dest/'manifest.json'),
                seconds=resources['seconds']+validation_process['seconds'],
                peak_process_tree_bytes=max(resources['peak_process_tree_bytes'],validation_process['peak_process_tree_bytes'])))
        except BaseException as exc:
            write_json(attempt/'failure.json',dict(schema='bsfm.mesh.phase0.failure.v1',status='failed',candidate=candidate,
                run_spec_sha256=expected,input_transport=spec['input_transport'],provenance=provenance,
                reason=str(exc),traceback=traceback.format_exc(),completed_candidates=ledger,
                not_run=[x['id'] for x in chosen[len(ledger)+1:]],attempt_retained=True))
            write_json(root/'failure.json',dict(status='failed',attempt=str(attempt),reason=str(exc),completed_candidates=ledger))
            raise
        write_json(root/f"checkpoint-{len(ledger):02d}.json",dict(status='in_progress',completed=ledger))
    for row in ledger:validate_closed(root/row['candidate'],deep=False)
    write_json(root/'manifest.json',dict(schema='bsfm.mesh.phase0.study.v1',status='complete',experimental=True,synthetic=synthetic,
        run_spec=file_record(root/'run-spec.json'),input_transport=file_record(root/'inputs.npz'),probes=file_record(root/'probes.json'),candidates=ledger,production_mesh_selected=False))
    return root


def main():
    if '--validate-worker' in sys.argv:
        require(len(sys.argv)==5,'Validation worker arguments')
        write_json(sys.argv[4],validate_closed(sys.argv[2],sys.argv[3],final=False));return
    if '--worker' in sys.argv:
        require(len(sys.argv)==6,'Worker arguments');worker(*sys.argv[2:]);return
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--environment',type=Path,required=True);ap.add_argument('--run-root',type=Path,required=True)
    ap.add_argument('--response-root',type=Path,required=True);ap.add_argument('--expected-commit',required=True)
    ap.add_argument('--execute-phase0',action='store_true');ap.add_argument('--section',default='S10__WT5')
    args=ap.parse_args();require(args.execute_phase0,'Explicit Phase-0 execution command required')
    require(args.section=='S10__WT5','Only the six S10 pilot candidates are implemented/authorized by this interface')
    config=read_json(REPO/'config/mesh/phase0-harness.json');study=read_json(REPO/'config/mesh/study-design.json')
    validate_design(study,config)
    require(not args.run_root.exists(),'A fresh experiment destination is required')
    try:
        preflight(config['resources']['minimum_available_GiB'])
        data,provenance=real_inputs(args.response_root,args.section,args.environment,args.expected_commit)
    except BaseException as exc:
        args.run_root.mkdir(parents=True)
        write_json(args.run_root/'failure.json',dict(schema='bsfm.mesh.phase0.failure.v1',status='failed',phase='preflight',reason=str(exc),
            expected_commit=args.expected_commit,section=args.section,study_sha256=sha(REPO/'config/mesh/study-design.json'),
            harness_config_sha256=sha(REPO/'config/mesh/phase0-harness.json'),scientific_candidate_started=False))
        raise
    provenance.update(harness_config_sha256=sha(REPO/'config/mesh/phase0-harness.json'))
    run(data,provenance,args.environment,args.run_root,study,config)


if __name__=='__main__':main()
