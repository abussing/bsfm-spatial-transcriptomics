# Current BSFM handoff

Updated 2026-11-06. This is a continuation map, not a chronological work log.
Read [AGENTS.md](../AGENTS.md) and the [workflow guide](WORKFLOW_GUIDE.md).

## Current work and authority

The continuing task is to make the existing consolidated layers reusable across datasets:
input, normalization, gene selection, mesh, initialization, GPU sampling and
saved outputs. Preserve verified scientific methods and extend existing
interfaces. Avoid parallel wrappers, competing guides and dataset-name branches.
Leave-out experiment design is separate from this core cleanup.

The validated reusable-method subset is now on `main`, promoted from
`147f79e` on `review/gpu-workflow-consolidation-20261103`. It includes panel
provenance, preprocessing, configurable registry loading, the GPINIT input
contract connection and mesh runtime/boundary support. The promotion preserves
all existing main sampler numerical kernels and the GP/SVD fitting code.

The reviewed runtime subset from `1bb4493` is now on main: GPU kernel corrections,
controllers, periodic storage/restart and prediction primitives. Experiment
launchers remain on the review branch. This is not blanket acceptance of that branch. The old `wip/layer9-orchestration-20261103` branch at
`a87532ec30d6daacada3245e2cbeb105da4435ce` is historical evidence, not the work
to promote. Inspect local changes before updating any checkout.

The [workflow guide](WORKFLOW_GUIDE.md) owns the implementation map and remaining
work. The existing mesh module now contains the geometry-only outer-boundary
producer; its S10 vertices and triangles reproduce saved arrays exactly. See the
[existing mesh guide](mesh/OCTOBER26_CANONICALIZATION.md) for the interface,
source, validation and limitations. Shared GPU environment authentication is now extracted and connected to the
existing runtime entry, with deployment paths in a separate recipe. Six synthetic
authentication tests pass; the shared-command GPU validation below also passed. The existing mesh module now assembles final builder outputs into warp arrays,
and the runtime loader joins generic prepared/GPINIT artifacts with explicit
recipes. Thirteen assembly/mesh tests pass; one R integration is skipped. The
synthetic GP fit uses one thread because unchanged four-thread GPINIT also crashes
in this local Windows environment; the accepted config is unchanged. The shared `python -m bsfm.sampler.run` command now handles explicit deep/flat
recipes, phased retuning, periodic saving and same-run resume. Small real CPU
transitions passed for both models. The [bounded GPU validation specification](environment/shared-run-gpu-20261105/RUN_SPEC.json)
and pinned deep/flat recipes are prepared: one V100, four CPUs, 16 GiB, 30 minutes,
synthetic inputs only. All 16 fixture files and runtime input joins passed local
checks. After explicit approval, job `22020867` was submitted on 2026-11-05 from
clean commit `de816792848ee47720fee7cd5233e50a0aeaafce`. Source and all 16 fixture
files are mirrored and hash-verified on HPC. GPU validation passed in 5 minutes
47 seconds on node386: both deep and flat phased runs completed, and fresh-process
completed restarts preserved outputs without replay. This is bounded synthetic
execution evidence, not scientific fit quality. The first attempt (`22020849`) failed before validation because node398
has no shared `/work` mount; the identical retry excludes that node. The specification records
the exact checkout, output and scheduler log paths. See the workflow guide. Do not substitute the older boundary-carrier triangles
as the final mesh. The shared command consumes prepared artifacts; raw preprocessing and mesh
construction remain separate stages. This job uses synthetic inputs only.

## Where to find verified methods and evidence

| Topic | Existing reference |
| --- | --- |
| Scientific decisions and response | [Modeling response](decisions/MODELING_RESPONSE_HANDOFF.md) and [sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md) |
| Gene-selection rationale | [Recovered 91-gene rule](recovery/gene-panel-20261104/README.md); generic screening scope is in the workflow guide |
| Dataset import and preparation | [Dataset contract](preprocessing/DATASET_CONTRACT.md), including axolotl/CELINA provenance and GPINIT contract export |
| Mesh | [Accepted builder and boundary recovery](mesh/OCTOBER26_CANONICALIZATION.md) |
| Initialization | [Accepted GP/SVD method](initialization/C3_GP_SVD.md); existing preparation and initializer CLIs are connected |
| GPU execution/restart | [Periodic saving](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/147f79e/docs/recovery/gpu-workflow-20261103/PERIODIC_SAVING.md) and [completed gate evidence](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/147f79e/docs/recovery/gpu-workflow-20261103/PERIODIC_FINAL_EVIDENCE.json) |

Latest bounded local checks: 14 initialization tests and nine preprocessing
checks passed; nine mesh checks passed and one actual R integration test was
skipped because the recorded accepted environment was unavailable. The recovered boundary carrier passed the bounded S10 comparison; this is not
validation of arbitrary new tissue geometry. Executable relocation is
not environment or cross-platform mesh reproduction. Linux R mesh completion
remains unestablished by these checks.

GPU acceptance follow-up: the stale Layer-5 provenance assertion is corrected
on review commit `59d8416`. It authenticates the exact GPU-only roundoff guard
and the otherwise unchanged historical split body. Eleven fresh local checks
passed, including gradient checks, periodic/every-sweep exact endpoints,
interrupted recomputation, committed non-replay and parent binding. See the
[pinned receipt](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/59d8416/docs/recovery/gpu-workflow-20261103/PERIODIC_LOCAL_VALIDATION.json).
No sampler code changed. The subsequent [numerical reconciliation](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/1bb4493/docs/recovery/gpu-workflow-20261103/FIXED_GRADIENT_RESULTS.md#saved-reference-reconciliation-2026-11-04)
passed six exact historical/current comparisons, including adaptation and full
Gibbs state/RNG. Both implementations show the same saved-reference differences:
Layer-3 gradients at most 2.77556e-17; Layer 5 only one gradient hash, with all
stored numeric values matching. Fixtures and tolerances are unchanged. These
bounded failures are not consolidation-induced changes; the precise low-level
rounding cause remains unisolated. The runtime promotion preserves reviewed source
bytes and records its exact inventory and fresh main-checkout tests in the
[existing validation receipt](recovery/REUSABLE_WORKFLOW_VALIDATION_20261104.json).
No new GPU execution or blanket full-branch acceptance is claimed.

## External artifacts and environments

HPC connection: `abussing@login.rci.sc.edu`, SSH port `222`; interactive Duo.
Never store credentials. All submissions require the committed specification
and authorization required by AGENTS.md. Do not alter immutable running-source
checkouts or mix duplicate same-seed chains.

Canonical mirror:
`/work/abussing/bsfm-consolidation/canonical-artifacts-20261103`.
All 187 payload files (6,943,739,779 bytes) were independently verified at transfer.
Expected `transfer-receipt.json` SHA256:
`5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60`.
The mirror's `source-inventory.json` maps original Windows paths to payloads.
Verify the receipt when needed; do not repeat payload recovery or regeneration
just because source-machine paths differ. Scratch remains a computational mirror,
not archival storage. The [external manifest](external-artifacts.json) is a
historical source inventory; its pre-transfer absence claims are superseded by
this completed transfer.

The mirror includes `s10-preparation-v2`, `s10-mesh`, `sct-v2`, `raw` and receipts.
Use recorded platform-specific environments and run-script receipts, not copied
Windows environments or guessed package substitutions. See the [Linux review
results](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/147f79e/docs/sampler/linux-review-20261103/REVIEW_RESULTS.md) and GPU evidence above
for their distinct validation scopes and preserved failures.

Axolotl import is now hash-verified on HPC at
`/work/abussing/bsfm-consolidation/evidence/axolotl-screening-20261105/dataset-v1`.
The approved six-fit screening pilot is job `22021229`, submitted from clean
commit `07b884f7bf22190b7c83c07e8381e17d8252753e` on `defq-48core` with two CPUs,
8 GiB and ten minutes. It passed all ten tests and six fits, completing in 80
seconds on node284. The local six-fit pilot took about 46 seconds; spatial
fractions differ by at most 3.11e-15 across the two environments. The existing
screen CLI now supports resumable gene batches, preserving the GP fitting
function unchanged. Thirteen focused tests pass. The full-run specification is
recorded in the dataset validation receipt: eight CPUs, 32 GiB, up to 24 hours,
16 genes per saved batch. After explicit approval, full-screen job `22021465`
was submitted from clean commit `cc8276b3162ac1917b6c7b7caf14ffefc69cc161` on
`defq-48core`. It completed successfully in 3 hours 6 minutes 54 seconds:
1,037 batches, 19,309 GP fits and 1,674 genes passing the spatial gate in at least
one type. The user chose within-cell-type spatial fraction as the primary ranking.
A review of the top 12 per type covers 46 unique genes; four of 72 entries have
recorded minimum-length-scale warnings and remain visible. The existing dataset
receipt records the external HTML, image and CSV paths and hashes. No final
top-N panel is imposed; inspect these expression maps before choosing the panel.
The receipt records the job's output and scheduler log paths. The imported bundle's original local path,
hashes, 16,586 genes, 4,410 cells and six groups are recorded in the
[import receipt](preprocessing/DATASET_LAYER_VALIDATION.json). It reuses the
existing normalized response without another transformation. The user subsequently
selected all six cell types, all 4,410 cells and within-sample spatial screening.
The existing selector supports this explicit mode without fabricating animal
identities; the Johnston recurrence rule is unchanged. See the dataset guide for
recipes and response-unit-specific eligibility. The expression filter leaves
5,305 candidate genes in at least one type; the final spatial panel and sampler
fit remain unfinished.

## Existing experiment outputs (not live job status)

The S10 periodic fits use immutable commit
`cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414`. Outputs are under
`/work/abussing/bsfm-consolidation/evidence/holey-periodic-cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414/CONFIGURATION`,
with summaries at `predictions/MODEL/latest.npz`.
The four flat fits completed 1,000 production sweeps. Deep continuation jobs
22018064?22018067 were submitted; their latest status must be queried, not
inferred from this document. The [continuation receipt](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/147f79e/docs/recovery/gpu-workflow-20261103/PERIODIC_RESUME_20261104.json)
records configuration/job mapping and exact resume boundaries. Convergence is
unassessed. These existing experiments are not the current core-cleanup task.

## Historical context

Detailed receipts remain at their existing locations. Superseded startup statuses,
failed attempts and the full shutdown transfer chronology remain in
[the previous handoff revision](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/ef53e81d1a00070f793e1e62bf263c8dd1f15e0c/docs/CURRENT_HANDOFF.md)
and Git history. They are not current instructions. Update this map in place;
do not prepend another running diary or create a duplicate archive document.
