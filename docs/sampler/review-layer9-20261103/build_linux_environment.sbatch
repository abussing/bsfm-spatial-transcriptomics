#!/bin/bash
#SBATCH --job-name=bsfm-layer9-env
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/layer9-env-%j.log
set -euo pipefail
commit="${1:?Exact generating commit required}"
checkout="/work/abussing/bsfm-consolidation/checkouts/$commit"
cd "$checkout"
export PYTHONNOUSERSITE=1 JAX_PLATFORMS=cpu JAX_ENABLE_X64=true
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec /work/abussing/bsfm-consolidation/environments/sampler-cpu-py311/bin/python -I \
  docs/sampler/review-layer9-20261103/build_linux_environment.py \
  --expected-commit "$commit" \
  --root /work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103
