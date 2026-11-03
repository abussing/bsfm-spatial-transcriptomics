#!/bin/bash
#SBATCH --job-name=bsfm-fixed-gpu
#SBATCH --partition=v100-16gb-hiprio
#SBATCH --gres=gpu:1
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=12:00:00
#SBATCH --output=/work/abussing/bsfm-consolidation/evidence/fixed-holey-%j.log
set -euo pipefail
commit="${1:?exact commit}"
configuration="${2:?configuration}"
model="${3:?model}"
cd "/work/abussing/bsfm-consolidation/checkouts/$commit"
test "$(git rev-parse HEAD)" = "$commit"
test -z "$(git status --porcelain)"
/work/abussing/bsfm-consolidation/environments/sampler-cpu-py311/bin/python - <<'PY'
import json, subprocess
from pathlib import Path
gate='51e1ee91d6cb3e54ce0e80baaaaa1c99e891c000'
p=Path('/work/abussing/bsfm-consolidation/evidence/real-replay-22015934/validation.json')
r=json.loads(p.read_text())
assert r['status']=='PASS' and r['commit']==gate
# All deployed sampler and runner bytes must match the complete-sweep gate.
paths=['src/bsfm/sampler','docs/holdouts/s10-grid-20261103/experiment.py',
       'docs/holdouts/s10-grid-20261103/gpu_run.py',
       'docs/holdouts/s10-grid-20261103/gpu_sample.sbatch']
subprocess.run(['git','diff','--exit-code',gate,'HEAD','--',*paths],check=True)
print('REAL_REPLAY_DEPLOYMENT_GATE_PASS',flush=True)
PY
export MKL_NUM_THREADS=1
exec bash docs/holdouts/s10-grid-20261103/gpu_sample.sbatch "$commit" "$configuration" "$model" fixed-order
