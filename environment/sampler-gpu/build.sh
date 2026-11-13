#!/bin/bash
# Restore a candidate environment only; this does not admit it for production.
set -euo pipefail
base_python="${1:?absolute Python 3.11.14 executable required}"
prefix="${2:?new absolute environment directory required}"
evidence="${3:?new absolute external evidence directory required}"
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo="$(cd -- "$here/../.." && pwd)"
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
unset PYTHONPATH PYTHONHOME
"$base_python" -I - "$prefix" "$evidence" "$repo" <<'PY'
import pathlib, platform, subprocess, sys
if sys.version_info[:3] != (3,11,14) or platform.system() != 'Linux' or platform.machine() != 'x86_64':
    raise SystemExit('Linux x86_64 Python 3.11.14 required')
repo=pathlib.Path(sys.argv[3]).resolve()
paths=[pathlib.Path(p) for p in sys.argv[1:3]]
if any(not p.is_absolute() or p.exists() or p.resolve().is_relative_to(repo) for p in paths):
    raise SystemExit('Use new absolute paths outside the checkout')
a,b=[p.resolve() for p in paths]
if a.is_relative_to(b) or b.is_relative_to(a):
    raise SystemExit('Environment and evidence directories must be separate')
if subprocess.check_output(['git','status','--porcelain'],cwd=repo,text=True).strip():
    raise SystemExit('Clean committed source required')
PY
mkdir -p -- "$evidence"
exec > >(tee "$evidence/build.log") 2>&1
git -C "$repo" rev-parse HEAD > "$evidence/source-commit.txt"
cp -- "$here/requirements.lock" "$evidence/requirements.lock"
"$base_python" -I -m venv "$prefix"
"$prefix/bin/python" -I -m pip --isolated install --require-hashes --no-deps --force-reinstall \
  --only-binary=:all: --report "$evidence/install.json" -r "$here/requirements.lock"
"$prefix/bin/python" -I -m pip --isolated check
"$prefix/bin/python" -I -m pip --isolated inspect > "$evidence/installed.json"
"$prefix/bin/python" -I - "$evidence" <<'PY'
import hashlib, importlib.metadata as md, json, pathlib, site, sys
root=pathlib.Path(sys.prefix).resolve(); out=pathlib.Path(sys.argv[1])
norm=lambda s:s.lower().replace('_','-').replace('.','-')
report=json.loads((out/'install.json').read_text())
expected={norm(p['metadata']['name']):p['metadata']['version'] for p in report['install']}
distributions=list(md.distributions())
actual={norm(p.metadata['Name']):p.version for p in distributions}
if actual != expected or len(distributions) != len(expected):
    raise SystemExit('Installed package closure differs from wheel installation report')
if site.ENABLE_USER_SITE or any(not pathlib.Path(d.locate_file('')).resolve().is_relative_to(root) for d in distributions):
    raise SystemExit('Packages outside the isolated environment')
def sha(p):
    with pathlib.Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
records={str(pathlib.Path(d.locate_file(f)).relative_to(root)):sha(d.locate_file(f))
         for d in distributions for f in d.files or [] if str(f).endswith('.dist-info/RECORD')}
receipt=dict(schema='bsfm.candidate-gpu-install.v1',status='INSTALLED_NOT_GPU_VALIDATED',
    prefix=str(root),python=sys.version,python_sha256=sha(sys.executable),packages=actual,
    record_hashes=records,source_commit=(out/'source-commit.txt').read_text().strip(),
    lock_sha256=sha(out/'requirements.lock'),install_report_sha256=sha(out/'install.json'),
    gpu_validated=False,production_admitted=False)
(out/'installation.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('Candidate environment installed and isolated; GPU validation remains required.')
PY
