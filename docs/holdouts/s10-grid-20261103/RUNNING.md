# Live S10 hole comparisons

All eight sampler jobs were RUNNING at the timestamp in RUNNING_RECEIPT.json.
This is a launch checkpoint, not a completed fit or convergence result. Check
Slurm and immutable production transactions before reporting later progress.

Exact generating commit: `27f9b3f0dfa4c1df2acc9e845633a8031069daea` on
`run/s10-holey-20261103`. This source-only branch avoids transferring the large
plot history; its sampler/test implementation matches review commit `44c9955`.
Subsequent fixes affect only preparation tracing, dependency-path resolution and
the GPINIT BLAS thread count. Accepted main has not merged these scientific changes.

| Circles | Diameter | Training / omitted | Deep job | Flat job |
| --- | --- | --- | --- | --- |
| 12 | width/16 | 4342 / 370 | 22013543 | 22013544 |
| 12 | width/8 | 3379 / 1333 | 22013546 | 22013547 |
| 8 | width/16 | 4472 / 240 | 22013549 | 22013550 |
| 8 | width/8 | 3756 / 956 | 22013552 | 22013553 |

All four preparations completed successfully (jobs 22013542/45/48/51), with
training-only K=12 GPINIT and 91 genes/three types. Exact seed hashes and counts
are in the receipt. Full-sample SCT reuse was explicitly approved by the user;
training-only centering, initialization and fitting remain enforced.

The run sequence is 50 NUTS tuning steps per factor, 50 bridge Gibbs sweeps,
100 NUTS retuning steps per factor in a child run, then 1,000 production sweeps.
K=12, L14/784 features, target_accept=.9, one chain per model/configuration.
Every completed sweep is checkpointed; every production sweep is retained.
Bridge draws are excluded from production prediction. Each sampler job has
4 CPUs, 16 GiB and 12 hours, allowing continuation beyond the five-hour meeting
target. No completion, convergence or number of usable draws is promised.

## Validation and resolved preparation failure

HPC job 22013528 at source commit 3530847 completed 0:0 in 54 seconds. Four
synthetic tests passed: both-model bridge/child-retuning/production/non-replay,
active-field reconstruction during conditional prediction, dense-Gaussian flat
target/gradient, and dense-Gaussian finite-feature predictive conditional.
The earlier local three-test run and separate warp test also passed. These are
focused extension checks, not a new all-layer regression or S10 mixing claim.

The first preparations (22013529/32/35/38) and tracing retry 22013541 segfaulted
inside SciPy Cholesky with the initializer's four-thread setting. One BLAS thread
resolved the failure; GP algorithm, nfit, data and parameters were unchanged.
Failed logs and prepared intermediate matrices are retained. Their eight
dependent sampler jobs were cancelled before they ran. No failed seeds were used.
scikit-learn 1.4.2 and joblib 1.4.2 are isolated under the validated dependency
prefix; the locked sampler environment was not modified.

## Locations and partial predictions

Output root:
`/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea`

Under each configuration: `prepared/`, `deep/bridge`, `deep/production`,
`flat/bridge`, `flat/production`. Production authority is
`MODEL/production/segments/segment/transactions/NNNNNNNNNNNN/` containing the
validated checkpoint/record pair. `run-ledger.json` is a repairable summary.
Logs: `/work/abussing/bsfm-consolidation/evidence/holey-JOBID.log`.

Use the exact generating checkout and locked sampler Python for prediction:

```sh
python docs/holdouts/s10-grid-20261103/predict_partial.py \
  circles12_diameter1of16 "$root/circles12_diameter1of16/prepared" \
  "$root/circles12_diameter1of16" deep \
  27f9b3f0dfa4c1df2acc9e845633a8031069daea --max-draws 20
```

Here `$root` is the output root above; set PYTHONPATH to the checkout's `src`,
CPU/x64 and single-thread variables as in sample.sbatch, and load gcc/12.2.0
and mpfr/4.1.0. Repeat for flat and the other configurations. This evaluates
numerical predictions and belongs in an allocated compute job, not the login
node. It reads a snapshot of completed production draws while sampling continues.
Never substitute bridge draws if production has not started. Prediction arrays
and a receipt are placed in each configuration's `predictions/MODEL/snapshot-N/`.

`render_comparison.py DEEP_SNAPSHOT FLAT_SNAPSHOT OUTPUT_DIRECTORY` creates an
HTML gallery with per-gene, three-cell-type observed/deep/flat spatial panels
and RMSE/MAE records. It uses NumPy/Matplotlib in a separate plotting environment;
its execution was checked with labeled synthetic arrays only. No real prediction
plots existed at this launch checkpoint.

Resume by rerunning the same sample.sbatch with the same exact generating commit,
configuration and model, only after verifying the old job is no longer a writer.
Do not regenerate preparation or change immutable specs/seeds/tuning on resume.
