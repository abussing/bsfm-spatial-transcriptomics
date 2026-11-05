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
mode="${2:-pilot}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONPATH="$PWD/src:$PWD/tests"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
exec /work/abussing/arka_trying_gpu_again/env/bin/python - "$commit" "$mode" <<'PY'
import hashlib,importlib.metadata as metadata,json,os,subprocess,sys,time,traceback
from pathlib import Path
repo=Path.cwd();commit=sys.argv[1];mode=sys.argv[2]
assert mode in ('pilot','full')
inputs=Path('/work/abussing/bsfm-consolidation/evidence/axolotl-screening-20261105')
base=Path('/work/abussing/bsfm-consolidation/evidence')
root=base/('axolotl-full-screen-'+commit) if mode=='full' else base/('axolotl-screen-pilot-'+os.environ['SLURM_JOB_ID'])
out=root/('attempt-'+os.environ['SLURM_JOB_ID']) if mode=='full' else root
out.mkdir(parents=True,exist_ok=False)
report=dict(status='RUNNING',commit=commit,commands=[],mode=mode,
            scope='Within-type GP screening; final model panel remains a separate decision')
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
    spec=record['single_sample_screening']['full_hpc_run_spec' if mode=='full' else 'next_hpc_run_spec']
    recipe_name='full-screen-recipe.json' if mode=='full' else 'pilot-recipe.json'
    recipe_key='full_recipe_sha256' if mode=='full' else 'pilot_recipe_sha256'
    for path,key in [('dataset-v1/dataset.json','dataset_manifest_sha256'),('dataset-v1/dataset.npz','dataset_payload_sha256'),(recipe_name,recipe_key)]:
        assert digest(inputs/path)==spec['inputs'][key],path
    report['versions']={p:metadata.version(p) for p in ['numpy','scipy','scikit-learn','threadpoolctl']}
    assert report['versions']=={'numpy':'2.1.3','scipy':'1.14.1','scikit-learn':'1.4.2','threadpoolctl':'3.6.0'}
    run([sys.executable,'-B','-m','unittest','test_screen_batches','test_single_sample_selection','test_dataset_preprocessing','test_spatial_screen','-v'],'tests')
    command=[sys.executable,'-B','-m','bsfm.preprocessing.spatial_screen','--dataset',str(inputs/'dataset-v1'),'--manifest-sha256',record['manifest_sha256'],'--recipe',str(inputs/recipe_name),'--output',str(root/'screen.json')]
    if mode=='full':
        assert int(os.environ['SLURM_CPUS_PER_TASK'])==8
        command+=['--checkpoint-dir',str(root/'batches'),'--batch-size','16','--workers','8']
    run(command,'screen')
    rows=json.loads((root/'screen.json').read_text())['rows']
    if mode=='pilot':assert len(rows)==6 and all(r['gene']=='AACS' and r['status']=='FIT' for r in rows)
    else:
        recipe=json.loads((inputs/recipe_name).read_text())
        assert len(rows)==len(recipe['genes'])*len(recipe['groups'])
    run([sys.executable,'-B','-m','bsfm.preprocessing.gene_selection','--sample-screen',str(root/'screen.json'),'--recipe',str(repo/'config/preprocessing/axolotl-gene-selection.json'),'--output',str(out/'selection.json')],'selection')
    report['screen_sha256']=digest(root/'screen.json')
    report['screen_rows']=len(rows)
    report['status']='PASS'
except BaseException:
    report['status']='FAIL';report['error']=traceback.format_exc();raise
finally:
    report['files']={p.name:dict(bytes=p.stat().st_size,sha256=digest(p)) for p in out.iterdir() if p.is_file()}
    (out/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
PY
