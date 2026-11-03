#!/bin/bash
#SBATCH --job-name=bsfm-hole-check
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/hole-check-%j.log
set -euo pipefail
commit="${1:?commit}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cpu JAX_ENABLE_X64=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD/docs/sampler/s10-subset-smoke-20261103:$PWD/docs/holdouts/s10-grid-20261103"
python=/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
out="/work/abussing/bsfm-consolidation/evidence/hole-check-$SLURM_JOB_ID"
mkdir "$out"
"$python" -B -m unittest test_meeting_extensions -v >"$out/extensions.log" 2>&1
"$python" -B -c 'from experiment_rule import load_rule; r=load_rule(); r.validate(); print(r.identity_json)' >"$out/rule.json"
deps="/work/abussing/bsfm-consolidation/environments/hole-gpinit-deps-$commit"
test ! -e "$deps"
"$python" -m pip install --no-deps --target "$deps" scikit-learn==1.4.2 joblib==1.4.2 >"$out/install.log" 2>&1
PYTHONPATH="$deps:$PYTHONPATH" "$python" -B -c 'import sklearn,joblib,numpy,scipy; print(sklearn.__version__,joblib.__version__,numpy.__version__,scipy.__version__)' >"$out/gpinit-versions.txt"
printf '%s\n' "$commit" >"$out/PASS"
