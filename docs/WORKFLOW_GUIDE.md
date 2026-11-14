# BSFM workflow guide

Use one workflow across datasets: import and verify the response, choose modeling
groups and genes, prepare the mesh and response, initialize, fit, and summarize
saved draws. Recipes provide inputs and settings; the methods remain shared.
Analysis results and execution histories belong outside the guidebook.

## Canonical route for a new dataset

Declare the population, modeling groups, response units, gene-selection criteria,
K, quadrature order, tuning/production lengths and save cadence in external recipes.
For a fit without labels, assign every modeled cell to one group; preparation then
subtracts one training mean per gene and the sampler uses one loading matrix.
For an ordinary full-population fit, use all selected cells as training cells and
an empty held-out list. Hole design is a separate experiment, not a preparation
requirement. Existing normalization is reused only after its meaning is verified.

| Stage | Canonical implementation and result |
| --- | --- |
| Import and response identity | [Dataset contract](preprocessing/DATASET_CONTRACT.md); explicit source adapter and `preprocessing.dataset.write_dataset` produce authenticated `dataset.npz` and `dataset.json` |
| Normalization | [SCT design](decisions/SCTRANSFORM_DESIGN.md), `sct_core.R`; alternatively explicit library scaling/log base in `preprocessing.normalization`; verified imported responses are not transformed again |
| Population and gene selection | `spatial_screen` and `gene_selection`: expression eligibility, spatial GP screening, expression/amplitude review and optional biological recurrence; freeze the justified panel externally using the [selection instructions](preprocessing/DATASET_CONTRACT.md#normalization-and-gene-selection) |
| Centering and preparation | `python -m bsfm.preprocessing.dataset ... --gpinit-contract`: training-only group means, ordered `training.npz`, `response.json` and `gpinit-input.json`; [arguments](preprocessing/DATASET_CONTRACT.md#prepare-a-response-using-explicit-names) |
| Mesh | [Accepted mesh method](mesh/OCTOBER26_CANONICALIZATION.md); `mesh.october26.inherited_geometry` supplies the boundary carrier, `build` constructs the final mesh, and `sampler_geometry` produces the sampler's geometry arrays |
| Initialization | `python -m bsfm.initialization.gp_svd ...`: [GP smooth/SVD method](initialization/C3_GP_SVD.md), producing `gpinit.npz` and its certificate; [arguments](preprocessing/DATASET_CONTRACT.md#connect-to-the-existing-initializer) |
| Quadrature | `sampler.registry_rule.load_registry_rule`: authenticate the explicit order's table; deep fixes outer ell_eta=0.14, learned-range flat rescales frequencies per factor |
| GPU fit and resume | `sampler.run` and `environment/hpc/sample.sbatch`: use the seven authenticated artifacts below, explicit phases and periodic saves; [stationary control](sampler/FLAT_CONTROL.md) |
| Saved output and prediction | Native retained records reconstruct the fitted response; `holdout_prediction` and `predictive_summary` condition on omitted locations when the experiment requires them |

The [modeling decisions](decisions/MODELING_RESPONSE_HANDOFF.md) and
[sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md) own scientific
choices. Historical recipes and fixtures test preservation, not universal defaults.
An accepted method is identified by its decision, promoted implementation and
scoped validation. A recovered candidate, a passing test or a recent run alone
does not select a method. The rejected M3/Phase-0 mesh redesign is not a second
supported builder. Keep unresolved choices explicit rather than promoting them
from old logs. [Historical evidence](recovery/README.md) is available when auditing
lineage; it is not required reading to start a new dataset.

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

### Moving to another HPC

Use the pinned installer, numerical validator and normal-launcher validation
below to establish a new GPU deployment. Treat the old deployment receipt as
evidence for its own environment, not an installer for another cluster:

| Step | What is available; what must be established at the destination |
| --- | --- |
| Source | Authenticate a clean checkout at an exact Git commit. A private repository needs GitHub access or a verified Git bundle from an authenticated clone. |
| Inputs | Transfer the seven prepared artifacts and their receipts; verify hashes and ordered identities. Moving a fit does not itself require repeating SCT, mesh construction or GPINIT. Building new inputs requires those stages' separate environments. |
| Environment | The [candidate Linux Python/wheel locks and installer](../environment/sampler-gpu/README.md) restore an isolated package set. The host and GPU driver remain explicit deployment inputs. Installation is not GPU validation. `config/sampler/hpc-gpu-runtime.json` still authenticates the older validated installation's entire package inventory and interpreter/file identities; it is not an installer or a receipt for this candidate. |
| Launch | `environment/hpc/sample.sbatch` and `initialize.sbatch` take explicit checkout, interpreter and module settings, described below. They invoke the same canonical CLIs and reject a dirty or incorrect source commit. Scheduler account, partition and resources belong in the external deployment manifest. |
| Hardware validation | Legacy recipes retain the V100/P100 authenticator. The [validated-runtime recipe](../environment/sampler-gpu/README.md#connect-the-validated-runtime-to-the-sampler) binds a pinned installation, numerical validation plan/report and exact tested GPU model. Its separate CLI validator exercises the normal launcher and completed restart using externally pinned synthetic inputs. Both numerical and CLI evidence are required before scientific fitting. |
| Restart | Ordinary checkpoint imports require matching runtime/device and spectral identities. The explicit runtime migration below creates a new lineage on a validated destination; it preserves the imported state, not bitwise cross-device future trajectories. |

Freeze destination paths, artifact hashes, environment build inputs, modules,
scheduler resources and source commit in an **external deployment manifest**.
Validate package integrity and isolation, then numerical checks and a small
deep/flat execution with saved-output/restart checks on the allocated GPU before
scientific fitting. Environment installation, passing execution checks, sampler
mixing and scientific output reproducibility are separate claims. Retain both
numerical and actual-CLI validation receipts for each destination; changing paths
alone does not establish either kind of validation.

## Run and resume prepared artifacts

From a clean checkout with its validated runtime active:

```text
python -m bsfm.sampler.run --recipe /external/analysis/run.json --output /external/run-root --commit FULL_COMMIT_SHA
```

Freeze the recipe in the external analysis directory before execution. `--commit` must equal the full
checkout HEAD. Output must be outside the repository. This command does not
submit a scheduler job, install software or preprocess data. HPC execution still
requires a frozen external job specification and explicit authorization.
New datasets and runs do not require a Git commit. Keep their manifests, panels,
resource settings and results together externally, pinned to the source commit.
Archive the exact recipe bytes and their SHA-256 with the submission receipt.
The runner binds the recipe hash into each phase and rejects changes on resume.
Legacy tracked recipes remain supported for historical runs; use their original
source commit rather than relocating an active run or editing its configuration.

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

Optional `pcg_maximum_iterations` sets a computational ceiling (integer 1?4096;
legacy default 80). The posterior RMS tolerance remains 1e-10. A larger ceiling
does not force extra iterations after convergence and does not change the model.
If the ceiling is reached, diagnose the same saved state before changing accuracy.

For stationary comparisons with learned spatial scales, supply optional
`flat_range_prior: {"median": 0.18, "log_sd": 0.25, "initial": 0.14}` with
`model: flat`. All three positive values must be explicit; choose them in the
prepared tissue units before fitting. Each factor learns its own range, which
is saved and used in prediction. Omitting this field preserves **fixed-range
flat** at 0.14. These are distinct baselines; see the
[control specification](sampler/FLAT_CONTROL.md). Deep does not accept this option.

Optional `initial_endpoint` pins an existing pre-sweep `endpoint.npz` by path,
bytes and SHA-256. Use a **new output root** and source commit for an explicitly
changed computational policy. The loader authenticates its original contract,
exact spectral chart, state, tuning and RNG streams; it imports completed tuning
without repeating it. The first phase's seed and tuning length must match the
source endpoint. Existing runs and their software/recipe identities stay intact.
This imports pre-sweep endpoints only; it is not a general checkpoint migration.

To continue a deliberately stopped periodic run under a new schedule, optional
`initial_checkpoint` pins five records (`path`, `bytes`, `sha256` each): `spec`
(`run-spec.json`), `inputs` (`input-receipt.json`), `genesis` (`endpoint.npz`),
`genesis_receipt`, and `boundary_receipt` at the chosen published sweep. Use a
separate output root and omit `initial_endpoint`. The complete published prefix
is authenticated under its original contracts; the parent need not be finished
and is never marked complete. Seed, target, exact spectral chart and runtime/device
identity must agree. The first phase must have `warmup_steps: 0`: it inherits
state, tuning and RNG streams without initialization or adaptation. Later phases
use the existing completed-parent readaptation interface. This is an explicit new
lineage, not permission to alter a same-run checkpoint or pool earlier draws.

For a deliberate move between validated GPU installations, optional
`checkpoint_runtime_migration` contains `schema: bsfm.checkpoint-runtime-migration.v1`
and the exact, distinct SHA-256 `source_environment_identity` and
`destination_environment_identity`. It requires `initial_checkpoint` and the
validated-runtime GPU recipe. The destination identity must equal the live
authenticated runtime; the source must equal the pinned original run spec.
The entire source prefix is still checked under its original contracts, including
the target, spectral chart, state, tuning and RNG. No source files or receipts are
rewritten. Saved arrays, hashes and contracts remain exact; recomputing physical
warps on the destination may differ by at most the existing absolute `2e-10`
dense-projector tolerance. The migration records the observed error at every
source boundary.
The derived ranges/scales also remain exact between saved arrays and diagnostic
records; their independent exponential recomputation permits at most `16*eps`
relative error (`eps` is float64 machine epsilon), recorded per boundary.
Migration lineages also permit at most `16*eps` relative error when verifying
saved alpha/zeta against their log/logit coordinates; the source import records
each such discrepancy. This validation context extends through destination
execution/restart without rewriting either representation. Non-migration chart
checks retain their exact inverse-or-forward rule.
Recomputed modal logarithms use the existing saved-geometry
`2e-10` tolerance, with identical finite/negative-infinity structure; their error
is recorded in the new input receipt. The saved spectral arrays are never
recomputed or replaced. Original checkpoints store only a digest of fitted
expression, not that derived matrix. During migration, its source and recomputed
destination digests are both recorded; exact underlying loading/eta, state,
position and RNG hashes remain mandatory. A digest alone cannot establish a
numerical error bound for this cross-BLAS recomputation. Original source boundary
digests are preserved for receipt-chain verification. Ordinary same-runtime reads
keep their exact fitted-expression comparison.
The new genesis records both runtime identities and excludes parent
draws. Subsequent trajectories can differ because floating-point computations
change across devices; exact interrupted restart applies within the destination.
Before moving scientific runs, validate an imported synthetic checkpoint on the
destination, including state/tuning/RNG equality at import, finite transitions,
interrupted restart and completed non-replay. Preserve health checks and assess
destination diagnostics before treating its draws as usable.

For a reviewed reduction after diagnostic replay, optional
`checkpoint_field_step_scales` maps **every** factor ID to a finite multiplier in
`(0,1]`; use 1 for unaffected factors. It requires `initial_checkpoint` and applies
once to the inherited first-phase field steps. The new genesis records original
tuning and the explicit scales. Mass matrices, hyperparameter steps, state and RNG
streams are inherited exactly. Resume never applies the reduction a second time;
later explicit adaptation phases estimate their own tuning. This changes the
computational schedule under a new recipe/output root, not the posterior target.
It is not an automatic tuning policy or a substitute for assessment through Gibbs
updates: fixed-conditional adaptation can work well during tuning and fail as the
other Gibbs quantities change.

Optional `diagnostics: adaptation_study_v1` records per-sweep parameter traces,
block energies, endpoint gradient norms, gauge-invariant loading strengths and
sweep times, alongside existing acceptance, divergence, trajectory and PCG
records. Retuning also saves exact incoming conditional arrays/positions for
replay; existing warmup histories retain positions, gradients and adapted mass.
Both blocks' adaptation histories can be audited from these records without
changing their transitions. Complete states and warps remain at the save cadence.
This policy stops at a published boundary if the same factor/block has >5%
divergences or mean acceptance <0.6 in both consecutive 25-sweep windows. It does
not automatically retune or advance to the next phase after stopping. Depth-cap
frequency is an efficiency warning only. Flat's joint alpha/zeta/range transition
occupies the first diagnostic block; the second block is an inactive compatibility
placeholder and is excluded from health review. Deep reviews both blocks. Active
blocks are selected from the model, never inferred from zero acceptance or steps.
These explicit review heuristics are
not convergence criteria; conditional energies from changing Gibbs targets must
not be used as one fixed-target E-BFMI series.

Each phase performs the specified NUTS tuning per factor followed by the specified
Gibbs sweeps. The first phase initializes; subsequent phases use the existing
readaptation controller and the completed parent's exact state/RNG. Specify tuning, bridge and production lengths in the recipe; no schedule is
implied by the command.
The minimum nonzero tuning length remains 20; zero is permitted only for the
first checkpoint-inheritance phase above. The periodic controller's existing zero-
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
the same GP/SVD CLI. The external JSON plan pins input files, ordered genes/groups,
factor count, initialization seed/subset size and output destination. Authenticate
the resulting certificate and freeze its output hashes in the sampler recipe
before GPU submission. Scheduler resources and approval remain explicit.

For GPU sampling, `environment/hpc/sample.sbatch COMMIT RECIPE OUTPUT` invokes
the same sampler command in the authenticated HPC CUDA environment. Pass the
approved partition and resource limits to `sbatch`; outputs remain external.

Both launchers require these exported deployment settings (absolute Linux paths):

```bash
export BSFM_CHECKOUT=/path/to/clean/pinned/checkout
export BSFM_PYTHON=/path/to/isolated/environment/bin/python
export BSFM_MODULES='site/module-version'  # explicitly empty if no modules are needed
export BSFM_CUDA_HOME=/path/to/cuda/toolkit # sampler only; must contain nvvm/libdevice/libdevice.10.bc
sbatch --account=ACCOUNT --partition=PARTITION --time=APPROVED_LIMIT \
  "$BSFM_CHECKOUT/environment/hpc/sample.sbatch" FULL_COMMIT_SHA /external/run.json /external/output
```

Use `initialize.sbatch FULL_COMMIT_SHA /external/plan.json` for initialization,
with that stage's authenticated Python environment. Module names are whitespace-
separated, loaded in order; no site module is implied. Slurm must export the
settings to the job (its normal `--export=ALL` behavior). The launchers locate their
shared setup in the checkout, including when Slurm executes a spooled script.
They preserve the existing sampler's x64, CUDA, BLAS-thread and preallocation
settings. Shell handoff tests cover spooling, quoted paths and rejection of
incorrect source/deployment settings; they do not validate a new GPU environment.

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
