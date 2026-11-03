#!/bin/bash
#SBATCH --job-name=bsfm-workflow-gate
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/workflow-gate-%j.log
set -euo pipefail
commit="${1:?exact reviewed commit}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true
export BSFM_EXPERIMENTAL_CUDA=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
export PYTHONPATH="$PWD/src:$PWD/tests:$PWD/docs/holdouts/s10-grid-20261103"
exec /work/abussing/arka_trying_gpu_again/env/bin/python -u docs/recovery/gpu-workflow-20261103/gpu_validation.py \
  --commit "$commit" --output "/work/abussing/bsfm-consolidation/evidence/workflow-gate-$SLURM_JOB_ID"
