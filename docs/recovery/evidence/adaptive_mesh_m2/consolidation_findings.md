# BSFM cleanup findings

## Authoritative assets found

The approved geometry and its prepared inputs are under:

`/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1`

Verified from its manifests and package result:

- 19 tissue sections;
- the frozen 91-gene panel;
- three cell types;
- four-stage fmesher geometry;
- 20-factor input assets;
- a spatially balanced 50% sample within each cell type, selected without
  expression screening;
- fresh per-section GP initialization from each retained subset;
- complete FEM/projector assets and hashes for every section;
- final package status `READY_FOR_CLOUD_GPU_PREFLIGHT`;
- CPU mesh validation and GP initialization reported as passed;
- no GPU smoke run for this package.

The exact code snapshot carried by that package dates from the authenticated
2026-10-14 source handoff. It contains the direct W1/W2 sampler, split-E NUTS,
active marginal whitening, and exact inactive-vertex marginalization.

## Rejected/stale campaign

The old campaign is under:

`/work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024`

Verified facts:

- it occupies about 23 GB;
- it contains pilots, quarantines, repeated tarballs, multiple input variants,
  adaptation runs, production continuations, and overlapping launch scripts;
- its active jobs use the old 20-factor/75%-cell inputs and rejected old mesh;
- its checkpoints cannot initialize a new-mesh run because the discretization,
  dimensions, and target assets differ;
- the historical ledger contains completed, failed, node-failed, pending, and
  cancelled tasks rather than one coherent completed campaign.

It should be retained as an immutable archive/evidence source, not used as the
working production directory.

## Conflicting run specifications found

The approved fmesher package currently carries three incompatible descriptions:

1. `README_L4.txt`: 20 factors, 50% cells, one chain per section, 100
   conditional warmup transitions per block, 50 discarded settling sweeps, and
   100 production sweeps. It explicitly calls this a preliminary panel and not
   a convergence claim.
2. `code/PRODUCTION_LAUNCH_CONTRACT.json`: 25-factor ceiling, four chains per
   section, two adaptation stages, 100 discarded settling sweeps, and 1,000
   retained sweeps per chain.
3. `code/CURRENT_CONFIGURATION.json`: stale simulation-study defaults including
   `K=5`, `G=32`, and 300 production sweeps.

None can silently override the others. The next implementation must generate
all launch commands and validation expectations from one frozen run-spec file.

## Workflow defects to eliminate

- Whole-array `afterok` dependencies allowed one failed task to strand unrelated
  sections as `DependencyNeverSatisfied`.
- Completion logic treated a scientifically usable warning certificate as a
  scheduler failure.
- Resource assumptions were shared across heterogeneous sections without an
  authenticated per-section memory gate.
- Historical cloud, pilot, 16 GB, 32 GB, K20, K25, 50%, and 75% launchers live
  together and are too easy to invoke accidentally.
- The old root mixes immutable inputs, source, environment libraries, logs,
  checkpoints, reports, tarballs, and discarded experiments.
- Monitoring required reconstructing status from Slurm output and scattered
  files rather than reading one authoritative ledger.

## Actions deliberately not taken

- No HPC files were deleted or moved.
- No currently running or queued jobs were cancelled.
- No checkpoint was altered.
- No production sampler code was changed.
- No new jobs were submitted.

