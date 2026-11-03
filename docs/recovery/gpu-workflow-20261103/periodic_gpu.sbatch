#!/bin/bash
#SBATCH --job-name=bsfm-periodic
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/periodic-fit-%j.log
set -euo pipefail
commit="${1:?exact commit}"; configuration="${2:?configuration}"; model="${3:?model}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
test "$(git rev-parse HEAD)" = "$commit"
test -z "$(git status --porcelain)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true BSFM_EXPERIMENTAL_CUDA=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
export PYTHONPATH="$PWD/src:$PWD/docs/holdouts/s10-grid-20261103"
python=/work/abussing/arka_trying_gpu_again/env/bin/python
"$python" - <<'PY'
import json,subprocess
from pathlib import Path
gate='2551f6d3c71be8956ab5d6f649371a2ad4615342'
r=json.loads(Path('/work/abussing/bsfm-consolidation/evidence/periodic-check-22016122/validation.json').read_text())
assert r['status']=='PASS' and r['commit']==gate
subprocess.run(['git','diff','--exit-code',gate,'HEAD','--','src/bsfm/sampler',
                'docs/holdouts/s10-grid-20261103/periodic_experiment.py',
                'docs/holdouts/s10-grid-20261103/periodic_prediction.py'],check=True)
print('PERIODIC_REPLAY_AND_PREDICTION_GATE_PASS',flush=True)
PY
prepared="/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/$configuration/prepared"
output="/work/abussing/bsfm-consolidation/evidence/holey-periodic-$commit/$configuration"
# The prediction worker is a separate CPU process and owns no sampler files/RNG.
JAX_PLATFORMS=cpu "$python" -u docs/holdouts/s10-grid-20261103/periodic_prediction.py \
    "$prepared" "$output" "$model" "$commit" --watch \
    > "/work/abussing/bsfm-consolidation/evidence/periodic-prediction-$SLURM_JOB_ID.log" 2>&1 &
predict_pid=$!
trap 'kill "$predict_pid" 2>/dev/null || true' EXIT
"$python" -u docs/holdouts/s10-grid-20261103/periodic_experiment.py \
    "$configuration" "$prepared" "$output" "$model" "$commit"
# A failed predictor makes job completion nonzero; sampler draws remain reusable.
wait "$predict_pid"
# Catch a final boundary published while the watcher's last update was in flight.
JAX_PLATFORMS=cpu "$python" -u docs/holdouts/s10-grid-20261103/periodic_prediction.py \
    "$prepared" "$output" "$model" "$commit" \
    >> "/work/abussing/bsfm-consolidation/evidence/periodic-prediction-$SLURM_JOB_ID.log" 2>&1
