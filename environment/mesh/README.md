# Isolated mesh environment: build and validation

Status: accepted after materialization, synthetic validation and fresh offline restoration. Baseline
`cfd00047d884021bed52194eb70189fd9cddc268`. These scripts build/check an
environment. They do not implement the Phase-0 scientific study.

See [the build report](../../docs/environment/MESH_ENVIRONMENT_BUILD.md),
[resolved versions](RESOLVED_PACKAGES.md), [specification](environment-spec.json)
and [validation contract](validation-spec.json).

## Isolation and lock coverage

The machine-local environment root is
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031`.
The existing SCT environment's R 4.5.3 runtime is reused read-only; the mesh
library is the separate `r-library/` beneath this new root. R runs with
`--vanilla`, an explicit `.libPaths(c(mesh_library, .Library), include.site=FALSE)`
and process-local R_LIBS_USER/R_LIBS_SITE. Every loaded non-base namespace is
required to come from the mesh library. The only remaining library path is the
immutable R distribution's base library; unrelated user/site/SCT package
libraries are excluded.

Python uses a new venv with `include-system-site-packages = false`. Every
resolved distribution is checked to reside inside it. The base Python 3.12.0
runtime and standard library remain external dependencies, recorded in
[runtime-lock.json](runtime-lock.json). No global package installation or PATH
modification is used. Run these scripts without Python `-O`: their assertions
are part of the validation.

- [r-source-lock.json](r-source-lock.json): exact source and Windows binary
  URLs, byte sizes, SHA-256, DESCRIPTION constraints, base packages and runtime.
- [r-packages.lock.json](r-packages.lock.json): complete resolved base/non-base
  package record, the permitted equivalent to renv.lock; **not** a renv-format
  file. Depends, Imports and LinkingTo are included; optional Suggests are not.
- [python-source-lock.json](python-source-lock.json): exact PyPI wheel URLs,
  byte sizes, SHA-256 and installation command.
- [python-requirements.lock.txt](python-requirements.lock.txt): exact versions
  and wheel hashes for offline `pip --require-hashes` installation.
- [python-freeze.txt](python-freeze.txt): full installed freeze, including pip.
- [runtime-lock.json](runtime-lock.json): reused runtime identities and the
  Python ensurepip bootstrap wheel identity. R distribution acquisition is
  inherited from the existing authenticated SCT runtime record.

Locks contain machine-local acquisition paths as evidence. Restoration rebases
archive/library paths while requiring the recorded runtime/package hashes.
Archive availability is not guaranteed indefinitely; retain the external
archives. Matching source/binary versions do not prove a reproducible source
build. The installed R packages are authenticated Windows binaries, not packages
compiled locally from those source archives.

## Original acquisition and installation

`acquire.py ROOT --resolve-r RSCRIPT` obtained official CRAN source archives and
resolved the 2026-03-12 Posit CRAN Windows 4.5 snapshot. Before installation it
checked fmesher's source DESCRIPTION, which requires R >= 4.1.0 and C++17, and
selected exactly 0.7.0. The resolved 33-package closure satisfied all 126 recorded
source/binary version constraints. Exact archives were installed locally by
`build.py ROOT --r`, which compares the shared R distribution tree before/after.

Python was created with the existing `C:\Program Files\Python312\python.exe`
using `-m venv ROOT\python`. Official PyPI wheel resolution used:

```text
numpy>=2,<3 scipy>=1.15,<2 h5py>=3.12,<4 psutil>=7,<8 jsonschema>=4.23,<5
```

The external `python-resolution.json` preserves pip's actual result, Python
compatibility tags and download records. `build.py ROOT --python` downloaded
those exact wheels, authenticated their hashes and installed offline. Future
restoration must use the locks, not rerun these unconstrained resolution steps.
The small installed-integrity record includes source hashes of these tools.

## Locked restoration into a different fresh root

After approval, use an absent external destination. `restore.py` refuses an
existing root or one inside the repository. It checks the supplied Rscript,
Python executable/DLL and ensurepip hashes; copies authenticated cached archives
when still available; with `--offline` it fails before creating the root if any
cache entry is missing or mismatched. It then invokes the same offline installers.
No package resolution or acquisition is permitted in this mode. Without that
flag, the original acquisition-capable interface remains available for a
separately authorized build.

```powershell
$meshRoot = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-REBUILD'
$meshR = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031\R-4.5.3\bin\x64\Rscript.exe'
$meshBasePython = 'C:\Program Files\Python312\python.exe'
& $meshBasePython -B environment/mesh/restore.py $meshRoot --rscript $meshR --python-base $meshBasePython --offline
```

The original installation and a second complete offline restoration have passed.
The [restoration receipt](../../docs/environment/MESH_ENVIRONMENT_RESTORATION.md)
records the exact executed command, package comparison, unchanged protected
environments and repeated synthetic outputs. The restoration-check root is
retained outside Git. A new build must pass the checks below before use.

## Minimal checks, never a real-data mesh

```powershell
$meshPython = Join-Path $meshRoot 'python\Scripts\python.exe'
$responseRoot = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2'
& $meshPython -B environment/mesh/validate.py $meshRoot --run-root $responseRoot --validation-name validation-review-complete
& $meshPython -B environment/mesh/audit.py $meshRoot
```

Use a new validation name for each rerun. Existing attempts are preserved and
never used as successful completion evidence. Only the canonical run manifest,
section registry and mesh design configuration are read; no response array or
H5AD is opened. R constructs a tiny unit-square synthetic mesh. Python reads its
explicit little-endian, row-major arrays and Matrix Market projector, writes a
tiny synthetic HDF5 file and writes a Matrix Market projector back for an exact
R readback. Actual synthetic arrays and process logs remain outside Git.

Semantic hashes are SHA-256 over row-major little-endian float64 coordinates,
query points and dense projector values, and int32 zero-based triangles;
dimensions, dtype and indexing are checked separately. These environment-test
hashes do not define a future production mesh serialization contract.

All thresholds are in [validation-spec.json](validation-spec.json). The memory
check exercises a live process tree; it is not a mesh-workload peak estimate.
This gate does not certify FEM accuracy, cross-platform mesh determinism, dense
eigensolve resource feasibility or real-section construction.
