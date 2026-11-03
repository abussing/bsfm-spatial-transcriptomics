#!/bin/bash
#SBATCH --job-name=bsfm-s10-tiny
#SBATCH --partition=defq-64core
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:30:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/s10-subset-smoke-%j.log
set -euo pipefail
commit="${1:?Exact committed source required}"
module load gcc/12.2.0 mpfr/4.1.0
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
export JAX_PLATFORMS=cpu JAX_ENABLE_X64=true OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$PWD/src:$PWD/tests"
python=/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
output="/work/abussing/bsfm-consolidation/evidence/s10-subset-smoke-$SLURM_JOB_ID"
mkdir "$output"
export TMPDIR="$output/tmp"
mkdir "$TMPDIR"
"$python" -B docs/sampler/s10-subset-smoke-20261103/check_rule_dimensions.py "$output/rule-dimensions.json" >"$output/rule-dimensions.log" 2>&1
"$python" -B docs/sampler/s10-subset-smoke-20261103/preflight.py "$output/preflight.json" >"$output/preflight.log" 2>&1
for phase in first resume nonreplay; do
  "$python" -B docs/sampler/s10-subset-smoke-20261103/smoke.py "$commit" "$output" "$phase" >"$output/$phase.log" 2>&1
done
