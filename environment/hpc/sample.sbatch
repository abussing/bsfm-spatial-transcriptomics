#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00
set -euo pipefail
commit="${1:?exact committed source required}"
recipe="${2:?committed sampler recipe required}"
output="${3:?external output directory required}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"
export JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true BSFM_EXPERIMENTAL_CUDA=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
exec /work/abussing/arka_trying_gpu_again/env/bin/python -u -m bsfm.sampler.run \
  --recipe "$recipe" --output "$output" --commit "$commit"
