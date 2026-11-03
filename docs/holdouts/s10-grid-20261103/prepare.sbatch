#!/bin/bash
#SBATCH --job-name=bsfm-hole-prep
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/hole-prep-%j.log
set -euo pipefail
commit="${1:?commit}"; configuration="${2:?configuration}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 JAX_PLATFORMS=cpu JAX_ENABLE_X64=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="/work/abussing/bsfm-consolidation/environments/hole-gpinit-deps-$commit:$PWD/src"
python=/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
root="/work/abussing/bsfm-consolidation/evidence/holey-$commit/$configuration"
"$python" -X faulthandler -B docs/holdouts/s10-grid-20261103/experiment.py prepare "$configuration" "$root/prepared" "$root" deep "$commit"
