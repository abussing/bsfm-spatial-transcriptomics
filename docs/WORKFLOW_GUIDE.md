# Reusable BSFM workflow: methods, recipes and current gaps

The repository is the scientific and operational reference for new datasets.
A method explains why and implements how; a recipe supplies dataset identities,
groups, units, populations and settings. Regression fixtures test preservation
of a recipe, rather than defining the only possible dataset.

This is the current workflow map, updated 2026-11-04. The reusable-method subset was promoted to main from review commit `147f79e`.
The runtime subset from review commit `1bb4493` is also promoted: GPU gradient
accumulation and acceptance-roundoff corrections, quadrature-derived joint-eta
dimensions, run controllers, periodic storage and prediction primitives. The complete
new-dataset workflow is **not yet available as one command**. Existing S10 runs
and exact source checkouts remain unchanged.

The core sequence is input, normalization, gene selection, mesh, initialization,
GPU sampling and saved outputs. Extend existing layer interfaces before adding
a wrapper or entry point. Dataset recipes supply identities and choices; they
do not define separate pipelines. Leave-out design and scoring are downstream
experiments, outside the current cleanup. Preserve historical evidence and exact
contracts; update this guide in place rather than adding competing current guides.

## Decision and implementation map

| Stage | Rationale / reusable implementation | Remaining coupling or gap |
| --- | --- | --- |
| Input | [Portable dataset contract](preprocessing/DATASET_CONTRACT.md), hash-pinned read/write and explicit RData adapter; real axolotl readback passes | Johnston raw adapter remains separate; more source formats require adapters |
| SCT | [Accepted design](decisions/SCTRANSFORM_DESIGN.md); `preprocessing/sct_core.R` accepts counts/depth | Extraction, depth policy and 300-gene validators are Johnston-specific; training-only SCT application unfinished |
| Library normalization | `preprocessing.normalization.log_library_size` takes explicit target sum and log base; distinct from SCT | Dense helper only; generic file ingestion and transform manifest needed |
| Existing response | Portable dataset manifest declares method/units/population/evidence; no automatic transformation | Original fit-population independence must be established separately |
| Expression eligibility | `preprocessing.gene_selection.expression_eligible`: explicit detection, level and nonconstancy thresholds | Thresholds depend on response units; no implicit transfer between normalization methods |
| Spatial selection | [Recovered rule](recovery/gene-panel-20261104/README.md); `select_spatial_genes` and CLI reproduce all 91 genes | `spatial_screen` supplies GP fits and technical-section medians; unknown biological replication requires an explicit policy |
| Centering | `dataset.prepare_response` exports named training/scoring arrays using training-only means; arbitrary group/gene counts pass sampler contract | Single-sample preparation joins GPINIT and final warp arrays through the existing runtime loader |
| Mesh | [Accepted builder](mesh/OCTOBER26_CANONICALIZATION.md); `mesh.october26.build` accepts cell/boundary paths and explicit authenticated runtime relocation | `sampler_geometry` assembles pinned final builder outputs with unchanged FEM routines; actual R environment validation remains separate. S10 `reproduce` is only a regression |
| GP initialization | [GP smooth/SVD](initialization/C3_GP_SVD.md); existing dataset CLI exports its contract via `--gpinit-contract`; both CLIs tested together | Prepared arrays, certificate and output hashes now join in `run_inputs.load_inputs`; accepted four-thread Windows runtime currently fails local checks; no initializer rewrite |
| Quadrature | `sampler.registry_rule.load_registry_rule(path, expected_sha256=..., order=L)` derives tensor shapes from L | Existing L4/L14/L16 arrays verified exactly. Other orders need authenticated tables. Target still scientifically fixes ell_eta=.14 |
| GPU sampler | Main contains reviewed GPU kernel corrections, periodic controllers, compact checkpoints and restart | Shared GPU authentication and generic prepared-input assembly available; scientific launcher and fresh GPU execution validation remain |
| Prediction | `holdout_prediction` and `predictive_summary` preserve the tested conditional prediction/mixture score | Sidecar and geometry/split lookup are S10-specific; generic reporting needed |

## Runtime interfaces and acceptance scope

`run_controller.RunController` composes initialization, tuning and Gibbs sweeps;
`run_readaptation.ReadaptationController` retunes from an authenticated parent.
`run_periodic.PeriodicRunController` and `PeriodicReadaptationController` publish
compact checkpoint/draw/diagnostic boundaries at the explicit save cadence.
Interrupted unpublished sweeps are recomputed; published boundaries are never
replayed. `run_incremental` preserves a checked in-memory transaction prefix.
These are existing implementations promoted from `1bb4493`, not rewritten kernels.

Callers supply a bound target, initialization arrays, explicit run specification,
input receipt and environment-authentication callback. K follows factor identities;
L follows an authenticated registry. Schedules and save cadence are explicit.
The target acceptance remains 0.9. GPU execution requires x64 and the existing
`BSFM_EXPERIMENTAL_CUDA=1` opt-in; that flag alone is not environment validation.
`run_gpu_environment.authenticate_gpu_environment` now provides the shared GPU
checks recovered from the [reviewed adapter](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/holdouts/s10-grid-20261103/gpu_run.py).
Deployment paths and receipt hashes live in `config/sampler/hpc-gpu-runtime.json`;
this is an environment recipe, independent of dataset, K, L and run length.
The existing `run_inputs.authenticate_environment(gpu_runtime=...)` dispatches
explicitly to it. `canonical_controller(..., gpu_runtime=...)` authenticates it
and exercises the original GPU callback before initialization. Omit the argument
only when intentionally requesting the existing CPU path. A GPU request fails
on CPU; it never falls back. Omitting `dataset_recipe` preserves registered S10 input assembly; supplying it
selects the generic prepared-artifact connection below.

For a caller already using the existing controller API:

```python
from pathlib import Path
from bsfm.sampler.run_storage import read_json
from bsfm.sampler.run_inputs import authenticate_environment

repo = Path("/path/to/exact/clean/checkout")
gpu_runtime = read_json(repo / "config/sampler/hpc-gpu-runtime.json")
for key in ("receipt", "p100_receipt"):
    gpu_runtime[key] = str(repo / gpu_runtime[key])
environment = authenticate_environment(gpu_runtime=gpu_runtime)
# Bind this environment into the existing software contract, and pass the same
# gpu_runtime arguments to canonical_controller or the controller callback.
```

The recovered authenticator retains package RECORD/source/bytecode checks,
interpreter/libdevice hashes, one V100/P100, float64 and explicit BLAS threads.
It adds receipt pins, site-package containment and duplicate-package rejection.
It is scoped to the recorded shared environment; this does not provision a new
CUDA environment or validate arbitrary GPU models. Six synthetic local tests
cover dispatch, tampering, devices and failure behavior. No new GPU execution
has validated the extraction yet. Immutable old runs keep their original adapter
and environment identities. The generic dataset/mesh/GPINIT connection below is available; a shared
scientific launcher remains unfinished.

Evidence retained at pinned revisions rather than duplicated here:

- [GPU accumulation and real K12/L14 replay gates](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/FIXED_GRADIENT_FINAL_EVIDENCE.json).
- [Periodic GPU state/RNG equality, interruption and scorer restart](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/PERIODIC_FINAL_EVIDENCE.json).
- [Historical/current numerical reconciliation](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/FIXED_GRADIENT_RESULTS.md#saved-reference-reconciliation-2026-11-04).
- [Main promotion inventory and local checks](recovery/REUSABLE_WORKFLOW_VALIDATION_20261104.json).

Old saved-reference bitwise failures remain recorded: both historical and current
implementations have the same discrepancies in the tested runtime. No fixtures
or tolerances were changed. Local CPU checks do not establish GPU speed, arbitrary
hardware equivalence, posterior convergence or a complete new-dataset workflow.
Immutable running checkouts and their continuation contracts are unchanged.

## Prepared artifacts to sampler inputs

Use the existing dataset CLI with `--gpinit-contract`, then the existing GP/SVD
CLI with explicit factor count, fitting count and seed. After the accepted mesh
builder finishes, `mesh.october26.sampler_geometry` consumes its pinned
`mesh_loc.csv`, `mesh_tv.csv`, `A_proj.mtx` and `geometry.json`. Supply the prepared
cell coordinates, names and source rows in exact order, plus their declared
coordinate system. It uses the existing projector checks, FEM assembly and
polynomial terms. Save the returned dictionary as an external NPZ; retain the
builder source hashes with that artifact. Do not pass boundary-carrier triangles
as final mesh output. The function validates geometry; it does not run R.

`run_inputs.load_inputs(files, factor_ids, dataset_recipe=recipe)` accepts exactly
seven file roles, each with `path`, `bytes` and independently pinned `sha256`:

| Role | Existing producer/output |
| --- | --- |
| `prepared` | Dataset preparation `training.npz` |
| `contract` | Dataset preparation `gpinit-input.json` |
| `response_manifest` | Dataset preparation `response.json` |
| `mesh` | NPZ of `sampler_geometry` arrays, including exact cell identities |
| `gpinit` | Existing initializer `gpinit.npz` |
| `certificate` | Existing initializer `certificate.json` |
| `rule` | Explicit registered quadrature JSON |

The recipe has `schema: bsfm.dataset-run-inputs.v1`, explicit `sample`,
`coordinate_system: october26_glial_min_max_span`, and `quadrature_order`.
That legacy chart name means the existing componentwise-minimum/common-maximum-
span transform and ordered y,x axes; it does not select glial cell types. Adapters
must supply the axes in that order. The builder's `geometry.json` echoes its
legacy config `units` field and cannot establish normalization by itself.
The explicit chart declaration and projector/coordinate joins remain required.

The loader verifies preparation metadata, ordered genes/groups, initializer
input/output identities and dimensions, mesh/cell alignment, and quadrature.
It returns the existing target, loading seed, eta seed and input binding. Pass
that same recipe to `canonical_controller(..., dataset_recipe=recipe)`; K comes
from explicit factor IDs and must match the initializer. Existing saved-genesis
restoration is reused. No HDF5 or scikit-learn import enters sampler loading.
This interface does not make imported normalization eligible for holdout scoring.

A synthetic 24-cell, two-group/two-gene/K2/L4 case passed real preparation and
GP/SVD initialization, final-output mesh assembly, repeated deterministic sampler
initialization, and finite target/gradient checks. Mixed certificates, reordered
mesh cells, changed files, wrong sample, K and L were rejected. Together with mesh
checks, 13 tests passed and one unavailable-R integration was skipped. The final
mesh fixture is synthetic: this is not a new R mesh build or GPU trajectory test.
The accepted four-thread GPINIT config causes a native access violation in the
current local Windows environment, including on unchanged tests. The connection
test uses a temporary one-thread config; the accepted config remains unchanged.
Restoring that four-thread environment is still unresolved.

## Reproduce the panel with the reusable selector

With dependencies installed and `src` on `PYTHONPATH`:

```text
python -m bsfm.preprocessing.gene_selection --animal-summary docs/recovery/gene-panel-20261104/EXPANDED_GP_ANIMAL_SUMMARY.csv --recipe config/preprocessing/johnston-gene-selection.json --output /external/path/selected-genes.json
```

Input is one CSV row per gene/celltype/animal, with `spatial_fraction` in [0,1]
or missing. Duplicate keys fail. The recipe supplies allowed types, threshold,
recurrence and optional expected animal count. Output includes every gene's
support/exclusion, source/recipe hashes and rationale. Existing output is never
overwritten. This selector does not fit GPs or reinterpret missing held-out scores.
Technical sections were aggregated by median upstream in the historical screen.

### Screening producer

`preprocessing.spatial_screen.screen_sample` supplies those upstream fits from
the existing dataset contract. Its recipe declares sample, ordered groups,
candidate genes, screening cells (`training_cells`) and numerical configuration.
`config/preprocessing/recovered-gp-screen.json` records the recovered settings;
its expression thresholds are explicitly in SCT units, not universal defaults.
The optional module CLI authenticates dataset and recipe hashes and records
package versions. `aggregate_animals` takes median spatial fractions across
technical sections and rejects duplicate blocks, conflicting identities and
unknown animals. It does not invent biological replication.

The fit was recovered by inspection from
`E:/johnston_brain/artifacts/GENE_REVIEW_20261004/review.py`, `fit_one`, lines
167–213, file SHA256
`8b590e72c4333a1241d5d3fca110cabc1b0cb43da7b5d3b8a8d96788b953173f`.
The Matérn-2.5 kernel, bounds, normalization, jitter, optimizer restart setting,
fixed per-group RandomState sampling and signal/(signal+noise) statistic are
preserved. The median aggregation is also visible in the already captured
`recovery/gene-panel-20261104/historical_gp_extension.py`. This bounded port
omits historical fitted-mean files, rendering, cache reuse and worker submission;
fit errors propagate instead of being hidden in sidecar error files. Expression
eligibility is explicit; it does not silently apply historical paper exceptions.

Two focused tests pass in the local Python environment with isolated
scikit-learn 1.4.2, joblib 1.4.2 and threadpoolctl 3.5.0: exact same-runtime
agreement with the inspected historical GP calculation on synthetic inputs,
fixed sampling, response-unit rejection, screening-population isolation,
technical-section aggregation and identity rejection. These are not a full
historical dataset reproduction or a justification for universal thresholds.

The original Johnston response recipe remains unchanged. Generic helpers are
not yet wired into its HDF5 production runner. `log_library_size` accepts raw
integer counts from the full measured gene universe before modeling selection;
caller supplies a target fixed independently or from training observations.
Integer checks cannot prove data provenance. Already-normalized responses enter
through an explicit imported-response contract, not through this transform again.
The Johnston natural-log SCT scale and axolotl library-normalized log2 scale are
different; no claim of interchangeability is made.

`center_from_training(response, cell_groups, training_mask)` fits means using
training cells only, applies those means to scoring cells, and fails if a group
has no training observations. It supports arbitrary group counts and names.

## Remaining implementation order

1. Dataset/response foundation implemented and checked on synthetic inputs and
   real axolotl import. Add a Johnston adapter/integration fixture; do not force
   identical normalization. See the dataset guide and validation receipt.
2. Screening GP producer and technical-section aggregation are ported with a
   bounded same-runtime test. Connect existing stage contracts without introducing
   a second preparation interface; replication policy remains explicit.
3. Generic preparation connects to the unchanged GPINIT command (14 tests passed
   in the earlier check; the current four-thread failure is recorded above).
   The existing mesh module now produces its inherited boundary carrier from
   normalized geometry: exact saved-S10 array agreement, nine mesh tests passed,
   one R integration skipped. Runtime relocation remains authenticated. The final geometry-to-sampler assembly now uses the existing FEM routines;
   actual R environment restoration remains separate.
4. The prepared-artifact assembly now accepts an explicit dataset recipe.
   Generalize the remaining scientific launcher boundary while
   preserving numerical kernels, saving and restart contracts. Validate on a
   second dataset before claiming generic execution.
5. Return to downstream scientific experiments separately after core integration.

Six focused tests pass: exact 91-gene recovery, same-type recurrence and duplicate
rejection, expression thresholds, library scaling/base, training-only centering,
and exact registry arrays for L4/L14/L16. These do not establish end-to-end axolotl
readiness, GPU performance or convergence. No new scientific run was launched.
