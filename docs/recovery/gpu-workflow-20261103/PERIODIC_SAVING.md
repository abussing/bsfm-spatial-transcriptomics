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

## Completed gate and deployment

Seven focused local tests passed. Real GPU job 22016122 passed all three checks
in `PERIODIC_FINAL_EVIDENCE.json`: exact periodic/every-sweep state and RNG,
fresh-process interruption/restart plus non-replay, and finite actual held-out
predictive scores with idempotent scorer restart. The two diagnostic draws are
validation evidence, not scientific posterior results.

All eight replacement jobs started and reached initial warmup on V100 GPUs:

| Holes | Diameter/tissue width | Deep job | Flat job |
| --- | --- | --- | --- |
| 12 | 1/16 | 22016141 | 22016142 |
| 12 | 1/8 | 22016143 | 22016144 |
| 8 | 1/16 | 22016145 | 22016146 |
| 8 | 1/8 | 22016147 | 22016148 |

Generating commit: `cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414`. Its sampler and
scoring source matches the GPU-tested commit; launcher checks this before fitting.
The launcher performs a final scoring drain after both fitting and the watcher
finish, covering a final publication concurrent with the watcher's last read.

Logs: `/work/abussing/bsfm-consolidation/evidence/periodic-fit-JOBID.log` and
`periodic-prediction-JOBID.log` in the same directory. The prediction log stays
empty until production draws arrive. Results live under
`evidence/holey-periodic-cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414/CONFIGURATION`.
Each model's cumulative result is `predictions/MODEL/latest.npz`, atomically
replaced per processed draw. It contains pointwise predictive density and
prediction moments, plus truth and cell/gene identities for plotting.

Measured saved boundary: 433,874-byte checkpoint and 1,104,751-byte retained draw,
plus small diagnostics/receipt. A thousand production sweeps save 101 draws,
approximately 155 MB for checkpoints/draws, plus fixed genesis and diagnostics;
the prediction summary is one overwritten file (4.5 MB in the diagnostic case).
An interruption can recompute up to nine unsaved sweeps. No scientific output
or convergence is claimed from this startup check.
