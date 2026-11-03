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
module load gcc/12.2.0 cmake/3.27.4 ninja/1.10.2
export CC=gcc CXX=g++
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
exec /work/abussing/bsfm-consolidation/environments/sampler-cpu-py311/bin/python -I \
  docs/environment/layer9-linux-20261103/build.py --expected-commit "$commit"
