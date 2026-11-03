#!/bin/bash
#SBATCH --job-name=bsfm-gpu-inventory
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=1G
#SBATCH --time=00:05:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/gpu-inventory-%j.log
set -euo pipefail
commit="${1:?commit}"
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
test "$(git rev-parse HEAD)" = "$commit"
test -z "$(git status --porcelain)"
hostname
nvidia-smi
