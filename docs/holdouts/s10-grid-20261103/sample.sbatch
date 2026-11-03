#!/bin/bash
#SBATCH --job-name=bsfm-holey
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/holey-%j.log
set -euo pipefail
commit="${1:?commit}"; configuration="${2:?configuration}"; model="${3:?model}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cpu JAX_ENABLE_X64=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/src"
python=/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
root="/work/abussing/bsfm-consolidation/evidence/holey-$commit/$configuration"
"$python" -B docs/holdouts/s10-grid-20261103/experiment.py run "$configuration" "$root/prepared" "$root" "$model" "$commit"
