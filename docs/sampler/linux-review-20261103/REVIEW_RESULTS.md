# Linux Layer-9 continuation review

Candidate source: `8abee709c592440dbc42e00fcdeb5a5da8d9b050` on
`review/layer9-portability-20261103`. This is a separate review candidate;
Layer 9 has not been merged into accepted main. No scientific job was submitted.

The earlier Windows review package is immutable historical evidence. This
report adds Linux evidence and supersedes its pending-Linux operational status.
The original initialization, genesis, checkpoint/record and RNG corrections
remain described in that package's implementation review and source map.

## Evidence and limits

- Job 22013414 used `a496b7cfc68a9c4d9858294c4a37fa851caaa562`:
  environment authentication, nine GPFS storage tests and all 46 focused
  Layer-9 tests passed. Full accepted-layer and mesh results are recorded in
  the job's final validation receipt separately.
  The ordinary accepted suite ran 195 tests with 27 failure entries (including
  subtests) and one error. Every failure traceback stops at a saved Windows
  reference comparison. The error is the Layer-6 test's fixed 3/2-ULP rounding
  plateau assumption, not a failure of an actual sweep. These checks are not
  counted as passes. The mesh stage discovered ten entries: seven passed, two
  R-dependent checks skipped, and one module failed import because this isolated
  sampler environment does not contain psutil. Job status was FAILED, exit 1:0,
  after 22 minutes 14 seconds; every planned stage completed.
- Job 22013415 used `5260e1c27406a22964263e937a406778184d25dd`:
  75 Layers 1-3 audit tests passed, and the authenticated historical/ported
  Layer-5 and Layer-6 calculations matched exactly in this Linux environment.
  Saved Windows fixtures did not all match. Fixture bytes remain unchanged;
  this independent audit does not turn ordinary regression failures into passes.
  Layer 4 was not included in that audit. Its public eta comparison differs by
  at most 4.4408921e-16 and rewhitened coordinates by 6.9388939e-17 in the
  retained tracebacks. A same-runtime Layer-4 comparison and measured chart
  rounding-boundary check are included as preflight gates of the proposed
  small S10 smoke, without editing accepted fixtures, tests or kernels.
- Job 22013417 used the final `8abee70` candidate: environment authentication
  and all ten storage tests passed. This separately verifies the final normalized
  path-containment guard added after the main validation job started. No sampler
  transitions ran in this job; the full 46-test run did not contain that guard.

The synthetic continuation contains two real sweeps per arm after 20 adaptation
steps per factor, with exact uninterrupted/resumed state and all four RNG
streams. Target acceptance remains 0.9. Initialization and sequential adaptation
chronology, distinct genesis, interrupted uncommitted recomputation, committed
non-replay, atomic checkpoint/record publication, projection repair and saved
chart restoration are exercised by the focused tests. No HDF5 runtime bridge
was added. These are synthetic mechanical checks, not canonical S10 execution.

The retained synthetic completion is `complete_with_warnings`: three warmup
divergences and two field-block sweep divergences. Convergence is not assessed.
No mixing, scientific performance, power-loss durability or protection against
external actors ignoring the writer lock is claimed.

Linux portability changes only authentication, locking/publication, and test
platform labels. GPFS requires the documented ownership-checked rename fallback.
The original bytecode/RECORD and GPFS failures remain preserved with their
corrections. `ACCEPTED_FILES.json` compares all 181 baseline source, test,
configuration, environment and schema Git blobs: none changed. New Layer-9
files are additions, not accepted Layer 1-8 edits.

## Reproducibility and next boundary

The exact runtime is
`/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python`.
Use the committed module/CPU/x64/thread settings in the run specifications.
Each scheduler job identifies an immutable checkout beneath
`/work/abussing/bsfm-consolidation/checkouts/<generating-commit>`.
Small receipts are preserved alongside this report; large logs and synthetic
payloads remain at their recorded HPC paths with hashes. The existing 187-file
canonical mirror was neither regenerated nor rehashed for these synthetic jobs.

Review the current implementation diff and file inventory together with the
original review, the additive `SOURCE_MAP.csv`, and all three distinct job
receipts. No result here silently waives a failed saved-fixture gate or the
unavailable canonical R environment.

The user requested a much smaller first smoke: 24 cells (eight per type), two
factors sliced from the registered full-data GPINIT, 20 warmup steps per factor
(the supported minimum), and two sweeps with a fresh-process restart between
them. The unchanged mesh/FEM coordinate frame is retained; active support is
recomputed for the selected projector rows, with all full FEM modes retained.
This derivative is explicitly labeled a smoke input, not a new canonical K=2
GPINIT preparation or a full-cell S10 validation. It needs a committed
launcher/run specification and explicit HPC approval. Full-data SCT
is not eligible for primary holdout scoring. Training-only preprocessing,
matched identity-warp execution and posterior prediction/scoring remain the
subsequent vertical-slice implementation work. No 19-section grid is launched.
