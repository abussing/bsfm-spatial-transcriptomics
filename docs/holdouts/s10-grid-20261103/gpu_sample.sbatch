#!/bin/bash
#SBATCH --job-name=bsfm-holey-gpu
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/holey-gpu-%j.log
set -euo pipefail
commit="${1:?commit}"; configuration="${2:?configuration}"; model="${3:?model}"
attempt="${4:-primary}"
[[ "$attempt" =~ ^[A-Za-z0-9_-]+$ ]] || { echo 'Invalid submission tag'; exit 2; }
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cuda JAX_ENABLE_X64=true
export BSFM_EXPERIMENTAL_CUDA=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
export PYTHONPATH="$PWD/src"
prepared="/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/$configuration/prepared"
output="/work/abussing/bsfm-consolidation/evidence/holey-gpu-$commit/$configuration"
if [ "$attempt" != primary ]; then
    output="/work/abussing/bsfm-consolidation/evidence/holey-gpu-$commit-$attempt/$configuration"
fi
exec /work/abussing/arka_trying_gpu_again/env/bin/python -u docs/holdouts/s10-grid-20261103/gpu_run.py "$configuration" "$prepared" "$output" "$model" "$commit"
