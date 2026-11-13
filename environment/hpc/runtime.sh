# Shared shell setup. Site choices belong in the external deployment manifest.
: "${BSFM_CHECKOUT:?set the absolute path of the pinned checkout}"
: "${BSFM_PYTHON:?set the absolute path of the isolated Python executable}"
: "${BSFM_MODULES?set the whitespace-separated module list (empty is allowed)}"
case "$BSFM_CHECKOUT" in /*) ;; *) echo 'BSFM_CHECKOUT must be absolute' >&2; exit 2;; esac
case "$BSFM_PYTHON" in /*) ;; *) echo 'BSFM_PYTHON must be absolute' >&2; exit 2;; esac
if [[ -n "$BSFM_MODULES" ]]; then
  read -r -a bsfm_modules <<< "$BSFM_MODULES"
  module load "${bsfm_modules[@]}"
fi
[[ -x "$BSFM_PYTHON" ]] || { echo 'BSFM_PYTHON is not executable' >&2; exit 2; }
cd -- "$BSFM_CHECKOUT"
[[ "$(git rev-parse HEAD)" == "$commit" && -z "$(git status --porcelain)" ]] || {
  echo 'Clean exact source checkout required' >&2; exit 2;
}
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"
