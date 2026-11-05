#!/bin/bash
#SBATCH --job-name=bsfm-ax-screen
#SBATCH --partition=defq-48core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/axolotl-screen-pilot-%j.log
set -euo pipefail
commit="${1:?exact committed source required}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONPATH="$PWD/src:$PWD/tests"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
exec /work/abussing/arka_trying_gpu_again/env/bin/python - "$commit" <<'PY'
import hashlib,importlib.metadata as metadata,json,os,subprocess,sys,time,traceback
from pathlib import Path
repo=Path.cwd();commit=sys.argv[1]
inputs=Path('/work/abussing/bsfm-consolidation/evidence/axolotl-screening-20261105')
out=Path('/work/abussing/bsfm-consolidation/evidence')/('axolotl-screen-pilot-'+os.environ['SLURM_JOB_ID'])
out.mkdir(exist_ok=False)
report=dict(status='RUNNING',commit=commit,commands=[],scope='Six-fit screening pilot, not final gene panel')
def digest(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def run(args,label):
    start=time.monotonic()
    with (out/(label+'.log')).open('wb') as f:
        result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
    report['commands'].append(dict(args=args,exit_code=result.returncode,seconds=time.monotonic()-start))
    result.check_returncode()
try:
    assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==commit
    assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
    record=json.loads((repo/'docs/preprocessing/DATASET_LAYER_VALIDATION.json').read_text())
    spec=record['single_sample_screening']['next_hpc_run_spec']
    for path,key in [('dataset-v1/dataset.json','dataset_manifest_sha256'),('dataset-v1/dataset.npz','dataset_payload_sha256'),('pilot-recipe.json','pilot_recipe_sha256')]:
        assert digest(inputs/path)==spec['inputs'][key],path
    report['versions']={p:metadata.version(p) for p in ['numpy','scipy','scikit-learn','threadpoolctl']}
    assert report['versions']=={'numpy':'2.1.3','scipy':'1.14.1','scikit-learn':'1.4.2','threadpoolctl':'3.6.0'}
    run([sys.executable,'-B','-m','unittest','test_single_sample_selection','test_dataset_preprocessing','test_spatial_screen','-v'],'tests')
    run([sys.executable,'-B','-m','bsfm.preprocessing.spatial_screen','--dataset',str(inputs/'dataset-v1'),'--manifest-sha256',record['manifest_sha256'],'--recipe',str(inputs/'pilot-recipe.json'),'--output',str(out/'screen.json')],'screen')
    rows=json.loads((out/'screen.json').read_text())['rows']
    assert len(rows)==6 and all(r['gene']=='AACS' and r['status']=='FIT' for r in rows)
    run([sys.executable,'-B','-m','bsfm.preprocessing.gene_selection','--sample-screen',str(out/'screen.json'),'--recipe',str(repo/'config/preprocessing/axolotl-gene-selection.json'),'--output',str(out/'selection.json')],'selection')
    report['status']='PASS'
except BaseException:
    report['status']='FAIL';report['error']=traceback.format_exc();raise
finally:
    report['files']={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in out.iterdir() if p.is_file()}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
PY
