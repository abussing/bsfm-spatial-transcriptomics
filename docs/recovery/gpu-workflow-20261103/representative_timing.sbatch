#!/bin/bash
#SBATCH --job-name=bsfm-real-timing
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/real-timing-%j.log
set -euo pipefail
commit="${1:?exact commit}"
module load gcc/12.2.0 mpfr/4.1.0 cuda/12.3
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true BSFM_EXPERIMENTAL_CUDA=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_FLAGS=--xla_gpu_cuda_data_dir=/work/apps/cuda/12.3
export PYTHONPATH="$PWD/src:$PWD/docs/holdouts/s10-grid-20261103"
for threads in 1 4; do
  export OPENBLAS_NUM_THREADS="$threads" OMP_NUM_THREADS="$threads" MKL_NUM_THREADS="$threads"
  /work/abussing/arka_trying_gpu_again/env/bin/python -u docs/recovery/gpu-workflow-20261103/representative_timing.py \
    --commit "$commit" --threads "$threads" \
    --output "/work/abussing/bsfm-consolidation/evidence/real-timing-$SLURM_JOB_ID/threads-$threads"
done
