import os
import subprocess
from pathlib import Path
import numpy as np
from scipy.io import mmread
from .identities import read_json,write_json,require,REPO
from .support import distance,edge_distance,target,enclosure
from .geometry import canonicalize,edges,diagnostics
from .projectors import project,validate


def build(points,observations,environment,work,h,collar_width,buffer,cap,config):
    work=Path(work);work.mkdir(parents=True,exist_ok=False)
    support,collar,outer=enclosure(points,collar_width,buffer,config['offset_directions'])
    loc=np.unique(np.vstack((support,collar,points.mean(axis=0)[None,:])),axis=0)
    rscript=read_json(REPO/'environment/mesh/runtime-lock.json')['R']['path']
    env=os.environ.copy();env.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
        TMPDIR=str(work.resolve()),TMP=str(work.resolve()),TEMP=str(work.resolve()),LANG='C',LC_ALL='C')
    history=[]
    for iteration in range(config['maximum_refinement_rounds']):
        step=work/f'round-{iteration:02d}';step.mkdir()
        for name,array in [('boundary.csv',outer),('locations.csv',loc),('observations.csv',observations)]:
            np.savetxt(step/name,array,delimiter=',',fmt='%.17g')
        np.savetxt(step/'boundary-quality.txt',target(distance(outer,collar),h,cap),fmt='%.17g')
        np.savetxt(step/'location-quality.txt',target(distance(loc,collar),h,cap),fmt='%.17g')
        write_json(step/'spec.json',dict(cutoff=config['cutoff'],minimum_angle=config['minimum_angle'],edge_cap=cap,projector_tolerance=config['projector_tolerance']))
        output=step/'output'
        command=[rscript,'--vanilla',str(Path(__file__).with_name('fmesher_bridge.R')),str(environment),str(step.resolve()),str(output.resolve())]
        process=subprocess.run(command,env=env,capture_output=True,text=True)
        log=process.stdout+process.stderr;(step/'process.log').write_text(log,encoding='utf-8')
        require(process.returncode==0 and 'stack imbalance' not in log.lower(),f'fmesher bridge failure: {log[-2000:]}')
        result=read_json(output/'result.json');require(result['index_base']==0,'Bridge index convention')
        original=np.fromfile(output/'vertices.f64',dtype='<f8').reshape(result['vertices'],2)
        tv=np.fromfile(output/'triangles.i32',dtype='<i4').reshape(result['triangles'],3)
        order=np.lexsort((original[:,1],original[:,0]))
        v,t=canonicalize(original,tv)
        a=mmread(output/'projector.mtx',spmatrix=True).tocsr()[:,order]
        validate(a,v,observations,config['projector_tolerance'])
        e=edges(t);length=np.linalg.norm(v[e[:,1]]-v[e[:,0]],axis=1)
        d=edge_distance(v[e[:,0]],v[e[:,1]],collar); limit=target(d,h,cap)
        bad=length>limit*(1+config['grading_relative_tolerance'])
        history.append(dict(iteration=iteration,command=command,vertices=len(v),triangles=len(t),
            violations=int(bad.sum()),max_target_ratio=float(np.max(length/limit))))
        if not bad.any():
            independent=project(v,t,observations,config['projector_tolerance'])
            delta=independent-a;error=float(np.max(abs(delta.data))) if delta.nnz else 0.
            require(error<config['projector_tolerance']*10,'Independent/fmesher projector mismatch')
            regions,report=diagnostics(v,t,support,collar,outer,h,cap)
            require(report['min_angle']>=config['minimum_angle']-1e-6,'Minimum angle not achieved')
            report.update(refinement_history=history,independent_projector_error=error,
                continuous_field_supplied=False,edge_constraint_certified=True,
                offset_radial_excess_bound=(collar_width+buffer)*(1/np.cos(np.pi/config['offset_directions'])-1))
            return dict(vertices=v,triangles=t,projector=independent,regions=regions,support=support,collar=collar,outer=outer,geometry=report)
        # Deterministic corrective seeds; fmesher still constructs all triangles.
        loc=np.unique(np.vstack((v,(v[e[bad,0]]+v[e[bad,1]])/2)),axis=0)
    raise ValueError(f'Grading mapping failed after {len(history)} rounds; no candidate success: {history[-1]}')
