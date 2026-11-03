#!/bin/bash
#SBATCH --job-name=bsfm-layer9-test
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/layer9-linux-%j.log
set -euo pipefail
commit="${1:?Exact source commit required}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export JAX_PLATFORMS=cpu JAX_ENABLE_X64=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/src:$PWD/tests"
export BSFM_HISTORICAL_DRIVER=/work/abussing/bsfm-consolidation/reviews/layer9-portability-20261103/payload/evidence/run_c3full_fixed_profile_nuts.py
exec /work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python -B -W error::ResourceWarning \
  docs/sampler/linux-review-20261103/validate.py "$commit" "$SLURM_JOB_ID"
