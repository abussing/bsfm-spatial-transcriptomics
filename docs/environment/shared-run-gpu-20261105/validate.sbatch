#!/bin/bash
#SBATCH --job-name=bsfm-shared-cli
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/shared-run-gpu-%j.log
set -euo pipefail
commit="${1:?exact commit required}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$PWD/src"
export JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true BSFM_EXPERIMENTAL_CUDA=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
exec /work/abussing/arka_trying_gpu_again/env/bin/python -u \
  docs/environment/shared-run-gpu-20261105/validate.py --commit "$commit" \
  --output "/work/abussing/bsfm-consolidation/evidence/shared-run-gpu-$SLURM_JOB_ID"
