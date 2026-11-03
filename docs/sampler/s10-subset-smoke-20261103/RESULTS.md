# L4 execution smoke completed

Job **22013500**, source `9823423a1315070b50c01a18f711d424f2b2b691`, completed
with scheduler exit 0:0 in **00:02:32**. Recorded batch MaxRSS was 819080K.
The scope was 24 actual S10 cells, 91 genes, two factors, L4/64 features,
53 active vertices and all 371 FEM modes. No mesh, SCT or GPINIT refit occurred.

- Dimension checks passed, including exact L16 old/new joint draw, coefficient,
  diagnostic, audit and RNG equality; L4 finite target/gradient and joint draw;
  mutation rejection; and rejection of L4 by the canonical L16 boundary.
- Both authenticated Layer-4 historical/port cases matched exactly on HPC.
  The exact chart contract passed its measured rounding-boundary checks.
- Both factors finished 20-step adaptation, then sweep 1 was committed.
- A fresh process restored the saved genesis/chart and completed sweep 2.
- Another process returned the identical completion with sweep execution
  forbidden, verifying no replay of completed work.

Completion is `complete_with_warnings`: **four warmup divergences**, **zero
sweep divergences**. This is an execution/restart success, not a convergence,
scientific accuracy, full-cell S10 or canonical L16 result. The small derivative
uses full-data preprocessing/GPINIT and is not a primary holdout experiment.

`job22013500-terminal.json` records accounting, selection and every retained
external file's size/hash. The stage receipts and submission identity are
preserved here byte-for-byte. External outputs are at
`/work/abussing/bsfm-consolidation/evidence/s10-subset-smoke-22013500`.
The original L16 timeout and its partial work remain separate at job 22013422.

The previous Linux-review inventory describes commit 1aecadb; the L4 source
inventory describes the generating source at 9823423. Verify each against its
own commit, not later documentation snapshots. Layer-9 source remains on the
review branch; this receipt does not merge it into accepted main.
