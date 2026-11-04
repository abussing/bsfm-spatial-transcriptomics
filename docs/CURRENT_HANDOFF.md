# Current BSFM handoff

Updated 2026-11-04. This is a continuation map, not a chronological work log.
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

GPU orchestration, periodic storage and experimental launchers remain on the
review branch. Their recorded execution evidence is not a blanket acceptance
of that branch. The old `wip/layer9-orchestration-20261103` branch at
`a87532ec30d6daacada3245e2cbeb105da4435ce` is historical evidence, not the work
to promote. Inspect local changes before updating any checkout.

The [workflow guide](WORKFLOW_GUIDE.md) owns the implementation map and remaining
work. The existing mesh module now contains the geometry-only outer-boundary
producer; its S10 vertices and triangles reproduce saved arrays exactly. See the
[existing mesh guide](mesh/OCTOBER26_CANONICALIZATION.md) for the interface,
source, validation and limitations. Current task: finish GPU orchestration acceptance before promotion; geometry
export/assembly integration remains the next reusable-interface task. Do not substitute the older boundary-carrier triangles
as the final mesh. A complete generic run command is not implemented yet.

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
rounding cause remains unisolated. Next assemble the GPU-runtime promotion scope
against its recorded environment, restart and interface evidence. No new GPU
execution or blanket full-branch acceptance is claimed.

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

Axolotl import is local, not confirmed mirrored to HPC. Its exact bundle path,
hashes, 16,586 genes, 4,410 cells and six groups are recorded in the
[import receipt](preprocessing/DATASET_LAYER_VALIDATION.json). It reuses the
existing normalized response without another transformation. No axolotl fitting
group, gene panel or scientific run has been selected by this cleanup.

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
