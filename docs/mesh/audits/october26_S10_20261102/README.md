# October 26 S10 reproduction: failed predecessor, retained

Subsequent [bounded localization](../october26_S10_localization_20261102/README.md)
identified an R integer/double angle-argument defect. The one corrected rerun
passed. The failure findings below describe the original attempt and are
preserved unchanged as historical evidence, not the latest capability status.

Baseline main and origin/main were clean and equal at
`4e362b6b3988e1b899d4250812ddfc4040beb819`. This audit describes **uncommitted
proposed code**, not a finalized production artifact. No commit or push occurred.

The [scope decision](../../../decisions/ADAPTIVE_MESH_WARP_BASIS.md) rejects M3/Phase-0
production selection and requests conservative historical reproduction. The
[computational-role report](../../OCTOBER26_CANONICALIZATION.md) records exact
historical file/line references and distinguishes source behavior from inference.

## Result

| Quantity | Historical reference | Port run |
| --- | ---: | ---: |
| Full geometry cells | 9,422 | 9,422 |
| MIC / AST / OGC geometry cells | 996 / 3,337 / 5,089 | 996 / 3,337 / 5,089 |
| Retained historical observations | 4,712 | 4,712 |
| Retained MIC / AST / OGC | 498 / 1,669 / 2,545 | 498 / 1,669 / 2,545 |
| Vertices | 371 | 330 |
| Triangles | 708 | 629 |
| Active, full observations | 168 | 167 |
| Active, historical half observations | 167 | 167 |
| Initial h | 0.13 | 0.13 |
| Selected h | 0.11290451085509637 | 0.11290451085509637 |

The first h attempt already differs: 313 historical total vertices versus 283,
although both have 132 active vertices. Count agreement on the retained active
subset alone is insufficient. The runner stopped at the geometry-count gate.
No tuning, rerun, invented boundary, fall-through success or promotion occurred.

Available closed-file checks on the failed geometry show projector row-sum
error 2.220446049250313e-16 and affine reconstruction error
1.1102230246251565e-15. These are mechanical coverage facts, not historical
reproduction. The historical geometry/projector/FEM comparisons and S10
full-to-active covariance check were not reached. The sampler-facing export was
not written. Construction runtime was not durably recorded before the failure;
it is not reconstructed from memory.

**Cause unresolved.** The explicit historical inputs are available in F. The A
audit originally covered only three sections and does not contain S10. Matching
the fmesher 0.7.0 version string does not establish identical historical runtime,
package build or external libraries. The current evidence does not distinguish
an implementation discrepancy from a runtime/input provenance discrepancy.
Do not label this a proven missing package or a scientific inadequacy of the
historical warp basis. Acceptance is blocked at this single reproduction gate.

## Evidence and command

- [reproduction.json](reproduction.json): measured counts, attempts, available
  projection checks, exact output location, and explicit uncompleted checks.
- [input-inventory.json](input-inventory.json): byte-identical copy of the
  pre-run input inventory, with paths, sizes and SHA-256. Every listed input
  rehashed unchanged after the run. Historical input certificate hashes for
  prepared mesh files and both observation archives passed; only geometry and
  identity members of NPZ files were decoded, never expression values.
- [source-identities.json](source-identities.json): the bounded source identities
  and line ranges. No sampler source was imported or executed.
- [rejected-phase0.json](rejected-phase0.json): preserves the scope reset and
  failed v1/v2 locations. All nine v1 recorded files still match size, hash and
  mtime. V2's failure record matches its previously reported SHA-256; this is
  not a claim of an unavailable prior whole-v2 inventory comparison. Neither
  historical experiment root was modified by this work.

Exact reproduction command (PowerShell, run once):

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031\python\Scripts\python.exe' -B -m bsfm.mesh.october26 `
  --historical-bundle 'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1' `
  --environment 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031' `
  --output 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_october26_S10_reproduction_20261102'
```

The machine-local external root contains the failed geometry, mesh RDS, projector,
log, session record, input inventory and failure record. It is retained. No
matrix, fitted object, archive or environment is added to Git. The R runtime was
the authenticated isolated SCT R 4.5.3 executable, with the separate accepted mesh
library: fmesher 0.7.0, sf 1.1-0, Matrix 1.7-4 and jsonlite 2.0.0. `.libPaths()`
and the process session are recorded; no environment was installed or modified.

## Tests

Seven new bounded tests passed. The complete suite also passed:
**126 tests, 0 failures, 0 errors, 0 skips, 158.828 seconds**, including existing
synthetic R-bridge integration checks. These do not run historical code or a real
sampler. No SCT normalization was performed.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:BSFM_MESH_INTEGRATION = '1'
& 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031\python\Scripts\python.exe' -B -m unittest discover -s tests -v
```

The numerical code and configuration are unchanged since that test run. No
historical S10 rerun is authorized by this report. Return for review at the
failed reproduction gate; do not promote the 330-vertex output as a substitute.

## Proposed changed-file inventory

All changes remain unstaged and uncommitted:

```text
AGENTS.md
CAPABILITIES.md
config/mesh/october26-warp-basis.json
docs/decisions/ADAPTIVE_MESH_DESIGN.md
docs/decisions/ADAPTIVE_MESH_WARP_BASIS.md
docs/mesh/OCTOBER26_CANONICALIZATION.md
docs/mesh/PHASE0_HARNESS.md
docs/mesh/audits/october26_S10_20261102/README.md
docs/mesh/audits/october26_S10_20261102/input-inventory.json
docs/mesh/audits/october26_S10_20261102/rejected-phase0.json
docs/mesh/audits/october26_S10_20261102/reproduction.json
docs/mesh/audits/october26_S10_20261102/source-identities.json
src/bsfm/mesh/october26.py
src/bsfm/mesh/october26_builder.R
tests/test_mesh_october26.py
```

Checks passed for 63 relative documentation links, JSON parsing, Python syntax,
credential patterns, small-file/allowed-file inventory, historical source-mesh
certificate hashes and all pre-run input hashes. `git diff --check` passed;
untracked files were checked separately for trailing whitespace. Nothing is staged.
No full production schema is claimed for this failed regression proposal.
