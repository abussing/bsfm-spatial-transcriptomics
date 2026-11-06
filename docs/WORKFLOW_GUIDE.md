# BSFM workflow guide

Use one workflow across datasets: import and verify the response, choose modeling
groups and genes, prepare the mesh and response, initialize, fit, and summarize
saved draws. Recipes provide inputs and settings; the methods remain shared.
Analysis results and execution histories belong outside the guidebook.

## Methods and interfaces

| Stage | Implementation and rationale |
| --- | --- |
| Import and response identity | [Dataset contract](preprocessing/DATASET_CONTRACT.md); `preprocessing.dataset` and explicit source adapters |
| Normalization | [SCT design](decisions/SCTRANSFORM_DESIGN.md), `sct_core.R`; alternatively explicit library scaling/log base in `preprocessing.normalization`; verified imported responses are not transformed again |
| Population and gene selection | Dataset recipes declare groups; `gene_selection` and `spatial_screen` implement expression eligibility, GP screening and optional biological recurrence; the dataset guide explains expression support and amplitude review |
| Centering and preparation | `dataset.prepare_response`: training-only group means, exact cell/gene ordering and GPINIT contract export |
| Mesh | [Accepted mesh method](mesh/OCTOBER26_CANONICALIZATION.md); `mesh.october26.build` and `sampler_geometry` |
| Initialization | [GP smooth/SVD method](initialization/C3_GP_SVD.md); `initialization.gp_svd` |
| Quadrature | `sampler.registry_rule.load_registry_rule`: explicit order and authenticated tables; the accepted target fixes ell_eta=0.14 |
| Fit and resume | `sampler.run`: explicit deep/flat, CPU/GPU, factor count, phases and periodic save cadence |
| Prediction | `holdout_prediction` and `predictive_summary`; experimental split design is separate from core preparation |

The [modeling decisions](decisions/MODELING_RESPONSE_HANDOFF.md) and
[sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md) own scientific
choices. Historical recipes and fixtures test preservation, not universal defaults.

## Runtime contract

`RunController` initializes and tunes; `ReadaptationController` starts from an
authenticated parent. Their periodic variants publish checkpoint/draw/diagnostic
boundaries at the declared cadence. Interrupted unpublished sweeps can be
recomputed; published boundaries cannot be replayed. Preserve exact RNG and
parent identities. Target acceptance remains 0.9.

GPU execution uses `run_gpu_environment.authenticate_gpu_environment`, float64,
explicit BLAS threads and the existing `BSFM_EXPERIMENTAL_CUDA=1` opt-in. The flag
alone is not validation. Deployment pins are in
`config/sampler/hpc-gpu-runtime.json`. Authentication checks package/source,
interpreter/libdevice, receipt and supported-device identities. It does not
provision an environment or validate arbitrary hardware. An explicit GPU request
fails on CPU rather than silently falling back.

## Run and resume prepared artifacts

From a clean checkout with its validated runtime active:

```text
python -m bsfm.sampler.run --recipe config/sampler/YOUR_RUN.json --output /external/run-root --commit FULL_COMMIT_SHA
```

Create and commit the recipe before execution. `--commit` must equal the full
checkout HEAD. Output must be outside the repository. This command does not
submit a scheduler job, install software or preprocess data. HPC execution still
requires a committed job specification and explicit authorization.

The recipe contains exactly these fields:

| Field | Meaning |
| --- | --- |
| `schema` | `bsfm.sampler-run.v1` |
| `backend` | Explicit `gpu` or `cpu`; GPU requests cannot fall back to CPU |
| `model` | `deep` or `flat`; use a distinct recipe/output root for each comparison arm |
| `chain_id`, `factor_ids`, `seed` | Explicit chain, ordered factor identities (K), RNG seed |
| `files` | Pinned artifact records described below |
| `dataset_recipe` | Prepared-input recipe below; null selects the original S10 registration adapter |
| `gpu_runtime` | Full GPU authenticator arguments; null for CPU |
| `phases` | Ordered records containing `run_id`, `warmup_steps`, `sweeps`, `save_every` |

Each phase performs the specified NUTS tuning per factor followed by the specified
Gibbs sweeps. The first phase initializes; subsequent phases use the existing
readaptation controller and the completed parent's exact state/RNG. Specify tuning, bridge and production lengths in the recipe; no schedule is
implied by the command.
The minimum tuning length remains 20. The periodic controller's existing zero-
settling restriction remains; bridge phases are separate runs. Only the last
phase supplies final production draws; do not pool earlier bridge draws.

Relative artifact and GPU deployment paths resolve against the recipe directory.
When embedding `config/sampler/hpc-gpu-runtime.json`, adjust its receipt paths to
that directory or use absolute deployment paths. The command sets x64, explicit
JAX CPU/GPU platforms and thread counts before importing JAX. GPU keeps a CPU
host device available for the existing callback preflight. Environment, artifact,
recipe and software identities are bound into each existing run contract.

Repeat the same command to resume. It authenticates completed parents and does
not retune or replay committed work. Changing the recipe, commit or runtime is
not same-run resume and is rejected by the immutable contracts. Each phase writes
to `OUTPUT/RUN_ID/segments/segment`; `boundaries/SWEEP/` holds the existing compact
checkpoint, retained draw, diagnostics and receipt. Saving remains first, every
configured cadence and final sweep. Per-sweep diagnostics cover unsaved sweeps;
interruption may recompute them from the last committed boundary.

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

For HPC initialization, `environment/hpc/initialize.sbatch COMMIT PLAN` invokes
the same GP/SVD CLI. The tracked JSON plan pins input files, ordered genes/groups,
factor count, initialization seed/subset size and output destination. Authenticate
the resulting certificate and freeze its output hashes in the sampler recipe
before GPU submission. Scheduler resources and approval remain explicit.

## Validation scope and remaining gaps

Bounded synthetic GPU validation covers deep/flat phased execution and completed
restart without replay. It does not establish scientific fit quality, convergence
or arbitrary hardware equivalence. Evidence is linked, not retold here:

- [Shared-command GPU specification and validation reference](environment/shared-run-gpu-20261105/RUN_SPEC.json).
- [Accepted runtime inventory and checks](recovery/REUSABLE_WORKFLOW_VALIDATION_20261104.json).
- [GPU numerical and restart evidence](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/PERIODIC_FINAL_EVIDENCE.json).
- [Historical/current numerical reconciliation](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/FIXED_GRADIENT_RESULTS.md#saved-reference-reconciliation-2026-11-04).
- [Preprocessing evidence index](preprocessing/DATASET_LAYER_VALIDATION.json).

Remaining limitations must not be hidden by generic interfaces:

- Dense response storage and single-sample preparation; additional source formats
  require explicit adapters. Legacy raw extraction and production wrappers retain
  dataset coupling.
- Training-only SCT application is unfinished. Imported full-population
  normalization does not establish independent holdout preprocessing.
- Canonical mesh-output reproduction on Linux is not established. Authenticate
  the R environment separately; boundary-carrier triangles are not final mesh output.
- The accepted four-thread GP initializer fails in the recorded Windows environment.
  One-thread interface checks do not establish restoration of that environment.
- Prediction primitives are reusable, but the experiment sidecar/reporting adapter
  retains dataset-specific lookup logic.
- Generic interfaces and small synthetic checks do not establish a complete
  scientific workflow on every new dataset. Validate each required environment
  and input join before claiming end-to-end readiness.

These are implementation/validation gaps, not a queue of analysis sessions. Keep
live job status, selected example genes, timing anecdotes and experiment results
in external run records.
