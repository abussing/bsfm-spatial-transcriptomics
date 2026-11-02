# Phase-0 synthetic implementation review

Status: **synthetic validation passed; harness approved for Phase 0 only**.
Review baseline: `2afcfc99a4e0d52a206ddfb2a559b57ed6fa94f1`.
The original evidence below was generated from uncommitted review code.
The [acceptance rerun](acceptance.json) and [complete acceptance test log](acceptance-tests.txt)
record validation after the approval wording changes. The 21-degree minimum
angle and other mechanical settings are approved for Phase 0 and remain
provisional for production. Real S10 execution needs separate authorization
against the exact committed harness. No real S10 arrays or candidate meshes were used;
no mesh was selected for production. See the [harness specification](../../PHASE0_HARNESS.md)
for the approved Phase-0 mapping, equations, output tree and future six-S10 command.

The original review's complete Python suite passed **112 tests: 31 mesh and 81 existing
tests, zero failures/errors/skips**, in 163.372 seconds. The integration tests
invoke the new R/fmesher bridge in fresh processes, not historical code. The
[complete test log](tests.txt), [machine-readable summary](summary.json),
[source/config/schema inventory](source-inventory.json),
[geometry table](geometries.csv), [range table](ranges.csv) and
[review checks](checks.json) preserve the evidence. Existing SCTransform R fits
were not rerun because this proposal changes no normalization code.
The original source inventory and check record describe the pre-acceptance
review capture. Their original findings are retained; acceptance.json authenticates
the sole configuration change (approval-status wording) and verifies that all
source, tests, schemas and numerical settings still match the reviewed files.
The acceptance rerun again passed all 112 tests, with no failures, errors or
skips, in 86.137 seconds. Five fresh R bridge calls had no warnings. Geometry
payload and per-range semantic hashes match both the original reviewed results
and the fresh-process repeat. See the [acceptance checks](acceptance-checks.json)
and [exact committed-file inventory](committed-files.txt).

The deterministic fixture has 289 all-cell/model observations, including
duplicate and near-coincident positions with distinct IDs. Its 256 probes are
64 per stratum and identical between fresh workers. Synthetic h, collar and
buffer values are explicitly separate from the real study factors.

| Synthetic candidate | Vertices | Triangles | Maximum edge/target ratio |
| --- | ---: | ---: | ---: |
| h=.35, collar=.15, buffer=.4 | 750 | 1,347 | 0.9681391751 |
| h=.35, collar=.15, buffer=.8 | 773 | 1,403 | 0.9804552945 |
| h=.22, collar=.15, buffer=.4 | 831 | 1,501 | 0.9950805664 |

All three have one component and satisfy the Phase-0-approved 21-degree minimum angle
within roundoff. The largest R-versus-independent-Python projector discrepancy
is 3.331e-16. The full numerical fixture uses all 750 modes and 48 active vertices.

| Mechanical measurement | Maximum observed |
| --- | ---: |
| Projector row-sum error | 0 |
| Affine coordinate reconstruction | 2.220e-16 |
| FEM identity error | 1.915e-15 |
| Generalized eigen residual | 8.356e-15 |
| Mass orthogonality error | 3.331e-15 |
| Independent dense precision-power oracle, relative | 1.897e-15 |
| Full-to-active covariance discrepancy | 0 |
| Projected full-to-active discrepancy | 0 |
| Root reconstruction, relative | 1.192e-15 |
| Root derivative identity, relative | 1.154e-11 |
| Covariance finite difference, worst of all tested steps | 8.070e-7 |
| Root finite difference, worst of all tested steps | 1.180e-6 |
| Covariance finite difference, worst range's best step | 8.826e-11 |
| Root finite difference, worst range's best step | 8.419e-9 |

The end-to-end numerical fixture uses ranges .3, 1 and 3; independent dense
oracles and derivative tests also include .15 and 5. Steps are 1e-3, 1e-4, 1e-5.
The real command retains the complete frozen 23-range grid, but that full grid
has **not** been executed on real geometry in this gate.

Excellent discrete agreement does not imply continuum accuracy. In this
deliberately small synthetic enclosure, maximum unit-variance errors at ranges
.3, 1 and 3 are respectively **0.5102, 0.2615 and 2.9085**. Covariance and
correlation discrepancies are recorded without hiding boundary effects or
normalizing the modeled covariance. The fixture is not a passing scientific
mesh design and its errors are not real-section results.

Fresh worker repeats have identical logical hashes for every geometry/identity/
sparse/eigen payload and all six per-range semantic quantities. File hashes need
not match because timings, commands and paths differ. The two computation runs
took 3.145 and 3.200 seconds; deep validation took 1.367 and 1.314 seconds.
Maximum sampled process-tree RSS was **445,366,272 bytes (about 425 MiB)**,
including the Python parent/worker and R child. Validator peak was 202,510,336
bytes. These small-fixture observations do not predict S10 cost.

Failure tests cover low headroom, a deliberately tiny memory ceiling with worker
termination, recursive child detection, durable failed-attempt retention, no
automatic fallback, missing/extra/incomplete artifacts, finalized overwrite
refusal, one-based/reversed/degenerate geometry, outside observations, raw-file
authentication before HDF5 opening, and corrupted coordinates, indices,
projectors, FEM matrices, regions, identity joins, eigenvectors, hashes and
manifest status. Semantic mutations fail even after file hashes are recomputed.
An isolated copy containing only the eight final files passes independent deep
validation; surrounding attempts are not authoritative dependencies.

Synthetic arrays and bridge diagnostics were preserved byte-for-byte outside Git:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_phase0_synthetic_20261102
```

This is a **machine-local** review location: 98 files, 14,287,332 bytes. The
summary records original temporary paths, final candidate manifest hashes and
logical hashes. Both the temporary and stable copies were retained. Only small
aggregate evidence enters this proposal; no HDF5, NPZ, Matrix Market data,
archives, environments or fitted objects are included in Git.

Post-test full content authentication matches the accepted mesh environment
tree (`6a51d946b43c097e6727330aac256a5190269297f1f097f5df00a431b47713db`)
and all 4,472 shared R runtime files, using the restoration receipt's inventory
encoding (`6870481507d5437200322ceb4ca56aabaeae9b6f42d9845b082ae4f057d57f76`).
No package installation or environment modification was performed.

Review limitations remain explicit: Windows-only reproducibility; monitored RSS
can overshoot between samples; circumscribed offset discretization and dense
boundary seeding may over-refine; the Phase-0 gap diagnostic is not anatomical
classification; physical units remain source_native. No real pilot, continuous
range certification, production thresholds or production mesh selection follows
from these synthetic passes.
