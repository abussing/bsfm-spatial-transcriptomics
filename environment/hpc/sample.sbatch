#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=24:00:00
set -euo pipefail
commit="${1:?exact committed source required}"
recipe="${2:?frozen sampler recipe required}"
output="${3:?external output directory required}"
: "${BSFM_CHECKOUT:?set the absolute path of the pinned checkout}"
case "$BSFM_CHECKOUT" in /*) ;; *) echo 'BSFM_CHECKOUT must be absolute' >&2; exit 2;; esac
source "$BSFM_CHECKOUT/environment/hpc/runtime.sh"
: "${BSFM_CUDA_HOME:?set the absolute CUDA toolkit path containing nvvm/libdevice}"
case "$BSFM_CUDA_HOME" in /*) ;; *) echo 'BSFM_CUDA_HOME must be absolute' >&2; exit 2;; esac
[[ -f "$BSFM_CUDA_HOME/nvvm/libdevice/libdevice.10.bc" ]] || {
  echo 'CUDA libdevice is missing' >&2; exit 2;
}
export JAX_PLATFORMS=cuda,cpu JAX_ENABLE_X64=true BSFM_EXPERIMENTAL_CUDA=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
export XLA_PYTHON_CLIENT_PREALLOCATE=false
export XLA_FLAGS="--xla_gpu_cuda_data_dir=$BSFM_CUDA_HOME"
exec "$BSFM_PYTHON" -u -m bsfm.sampler.run \
  --recipe "$recipe" --output "$output" --commit "$commit"
