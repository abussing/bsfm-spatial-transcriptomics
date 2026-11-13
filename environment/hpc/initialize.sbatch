#!/bin/bash
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
set -euo pipefail
commit="${1:?exact committed source required}"
plan="${2:?external run plan required}"
: "${BSFM_CHECKOUT:?set the absolute path of the pinned checkout}"
case "$BSFM_CHECKOUT" in /*) ;; *) echo 'BSFM_CHECKOUT must be absolute' >&2; exit 2;; esac
source "$BSFM_CHECKOUT/environment/hpc/runtime.sh"
export OPENBLAS_NUM_THREADS=4 OMP_NUM_THREADS=4 MKL_NUM_THREADS=4
exec "$BSFM_PYTHON" -u - "$commit" "$plan" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
from bsfm.initialization.gp_svd import load_input
commit,plan=sys.argv[1:]
assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==commit
assert not subprocess.check_output(['git','status','--porcelain'],text=True).strip()
assert Path(plan).is_file(), 'Run plan file required'
spec=json.loads(Path(plan).read_text());init=spec['initialization']
for record in spec['inputs'].values():
    p=Path(record['path'])
    assert p.stat().st_size==record['bytes'],str(p)
    assert hashlib.sha256(p.read_bytes()).hexdigest()==record['sha256'],str(p)
input_path=spec['inputs']['prepared']['path'];contract=spec['inputs']['contract']['path']
data=load_input(Path(input_path),json.loads(Path(contract).read_text()))
assert data['Y'].shape==tuple(spec['response_shape'])
assert data['gene_names'].tolist()==spec['genes']
assert data['cell_type_names'].tolist()==spec['groups']
command=[sys.executable,'-u','-m','bsfm.initialization.gp_svd','--input',input_path,
         '--contract',contract,'--output',init['output'],'--factors',str(spec['factors']),
         '--nfit',str(init['nfit']),'--seed',str(init['seed'])]
print('Validated inputs; invoking canonical GP/SVD initializer',flush=True)
subprocess.run(command,check=True)
print('Initialization completed; sampler launch is a separate step',flush=True)
PY
