#!/bin/bash
#SBATCH --job-name=bsfm-gpu-check
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/gpu-check-%j.log
set -euo pipefail
commit="${1:?exact commit}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
test "$(git rev-parse HEAD)" = "$commit"
test -z "$(git status --porcelain)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cuda JAX_ENABLE_X64=true
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 XLA_PYTHON_CLIENT_PREALLOCATE=false
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD/docs/sampler/s10-subset-smoke-20261103:$PWD/docs/holdouts/s10-grid-20261103"
python=/work/abussing/arka_trying_gpu_again/env/bin/python
output="/work/abussing/bsfm-consolidation/evidence/gpu-check-$SLURM_JOB_ID"
mkdir -p "$output"
nvidia-smi > "$output/nvidia-smi.txt"
"$python" -u docs/holdouts/s10-grid-20261103/gpu_validate.py "$output" "$commit"
