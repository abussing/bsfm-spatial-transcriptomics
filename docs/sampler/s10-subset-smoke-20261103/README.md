# Small S10 execution smoke proposal

Current retry: [L4_RETRY.md](L4_RETRY.md). The original L16 job 22013422
timed out before saved genesis. The user explicitly requested lower L for this
execution check. The current launcher uses L4 (32 frequencies, 64 columns) and
30 minutes of scheduler headroom; cell/factor/warmup/sweep counts are unchanged.
The text below describes the original L16 proposal at commit 1aecadb.

The user explicitly requested a small subset, few factors, short warmup and
very few iterations. RUN_SPEC.json fixes 24 cells, two factors, 20 warmup steps
per factor and two sweeps total, with a ten-minute scheduler cap. This replaces
the proposed full-cell first smoke; it does not validate a full-cell fit.

Preflight authenticates the original Layer-4 source files and compares both
recorded synthetic cases against the port in the same runtime. It also measures
the exact chart rounding boundary instead of assuming the Windows 3/2-ULP
plateau. Failure stops the job before S10 execution. Frozen regression fixtures
and accepted Layers 1-8 remain unchanged.

The runner first uses the existing authenticated full-input loader against the
committed S10 v2 registration. It then selects eight evenly spaced row indices
per type and the first two registered GPINIT factors. Full-data response values
and seed values are copied unchanged, without recentering, refitting or remeshing.
The full FEM matrices, vertices, coordinate frame and 371 modes remain. Only
projector rows and their exact active support change for the derivative.

This is an explicitly authenticated derivative entry, not a claim that the
strict canonical_controller accepts arbitrary subsets. The runner composes
RunController only after checking a clean exact Git commit, the locked runtime,
all eight registered parent artifacts, subset identities, and seed hashes.
The same checks run before execution and closure. Its persisted binding labels
the derivative and its ineligibility for primary holdout scoring. It does not
alter the registered preparation or replace the canonical full-input boundary.

One process runs warmup and sweep 1. Another restores the saved chart/genesis
and runs sweep 2. A third verifies completed non-replay with sweep execution
forbidden. Resume must reconstruct exactly the same input, software and run
bindings. Reports, selection identities and retained records are external under
the job-specific output path. Scheduler timeout means incomplete, never pass.

This is a mechanical acceptance exercise on the review branch. It does not
merge Layer 9 into main, assess convergence, score held-out cells or authorize
a larger fit. Successful continuation is useful even when the tiny warmup
records divergences; all warnings remain visible.
