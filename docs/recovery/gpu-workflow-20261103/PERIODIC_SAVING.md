# Periodic saving and held-out metrics

The user explicitly requested cancellation of all BSFM jobs and fresh runs with
periodic, inexpensive saving sufficient for leave-out metrics. All 24 named BSFM
jobs were canceled, including the eight f7ce414 fits; outputs are preserved.
Unrelated hurdle/cs jobs remain untouched. HPC cancellation receipt:
`evidence/gpu-workflow-audit-20261103/periodic-saving-cancellations.json`.

## New storage boundary

Save the first, every tenth and final complete sweep. One atomic directory holds
one compact restart checkpoint, one retained draw and diagnostics for intervening
sweeps. No duplicate checkpoint or archive projections. All spectral arrays are
omitted from compact checkpoints and reconstructed from the authenticated bound
geometry, whose complete chart is saved in genesis. The original checkpoint
metadata retains every array descriptor; the original Layer-7 validator verifies
the reconstructed bytes. This is a new codec, not a tolerance exemption.

Between boundaries the sampler continues in memory with the same scientific
updates, labels and RNG streams. On interruption, up to nine uncommitted sweeps
are recomputed from the last published boundary. Complete publication candidates
are validated and promoted; published boundaries are never replayed. Parent
readaptation uses the same existing initialization/adaptation code and chronology.
Old immutable every-sweep runs are not migrated or pruned.

Prediction retains the existing full draw fields (about 1.1 MB in the real test),
which are sufficient for finite-feature held-out prediction. Fixed geometry is
not repeated, and no prediction matrix is saved for every draw. A CPU sidecar
reads only production boundaries, uses a separate deterministic prediction RNG,
and atomically updates a single `predictions/MODEL/latest.npz`. It stores running
means, second moments, stable log-density sums, truth/identity fields and source
draw receipts. Reopening the scorer authenticates the source prefix and does not
double count. It never writes sampler files. Bridge draws are excluded.

The score averages per-draw normal densities including latent conditional
variance and observation noise, then takes the log. It is pointwise per
gene/cell, not a joint correlated-hole likelihood. The deep score Monte Carlo
integrates one conditional inactive-vertex warp realization per posterior draw.
Full-sample SCT remains the user-approved preliminary limitation.

## Authorized bounded validation and relaunch

`validate_periodic.sbatch`: one V100, four CPUs, 16 GiB, at most 30 minutes.
Three real K12/L14 diagnostic sweeps from the previously authenticated adapted
seed, cadence three to exercise an unsaved intermediate sweep. Compare states
and RNG exactly against the previous every-sweep gate; interrupt and resume in
fresh processes; confirm committed non-replay, compact sizes and actual held-out
log-density scoring, including scorer restart. No new warmup or scientific fit
in this validation job. Local tests additionally cover partial publication,
tampering, sparse cadence, parent binding and independent mixture-density math.

Only after the gate passes, relaunch the same four hole configurations/deep-flat
pairs, K12/L14, 91 genes/three types, initial50/bridge50/retune100/production1000,
one V100/four CPUs/16 GiB/12 hours per job. Saving is first/every10/final and one
BLAS thread. The scorer uses a separate CPU process within the same allocation.
Mechanical correctness does not establish convergence or a completion deadline.
