# Required capability map

This is the initial user-authored functionality inventory. It records required
capabilities, not claims that any historical implementation is authoritative.

For current machine-to-machine readiness, use the
[pipeline portability audit](docs/PORTABILITY_AUDIT.md). Checkpoint-specific
statements below retain their original scope and do not supersede later receipts.

## 1. Expression preprocessing

Recovery status: **historical normalization-recipe recovery completed through
B6; canonical scientific design approved; raw-input preflight and full-data
depth accepted; isolated canonical environment materialized; synthetic and
bounded S00 normalization validation accepted; canonical full-data production
implemented and production-validated for all 19 sections in v2**. See the
[production receipt](docs/preprocessing/audits/20261031_production_v2/README.md),
[canonical SCTransform decision](docs/decisions/SCTRANSFORM_DESIGN.md),
[environment decision](docs/decisions/SCTRANSFORM_ENVIRONMENT.md),
[SCTransform recovery](docs/recovery/SCTRANSFORM_PREPROCESSING.md) and
[evidence ledger](docs/recovery/SCTRANSFORM_EVIDENCE.md).

| Aspect | Status |
| --- | --- |
| Scientific response intent | Recovered: log1p(corrected counts). |
| Downstream exporter/handoff | Recovered: implemented behavior and recorded artifact links; actual sampler invocation is not certified. |
| Historical normalization implementation | Recovered writer recipes: 10 new, 3 regional reused, 6 sct_work reused; effective defaults/execution attribution remain incomplete. |
| Uniform cross-section comparability | Historical mixed-pipeline comparability remains unestablished. Canonical v2 uses the frozen uniform recipe and common depth across all 19 sections, with production validation. |
| Replacement design | Approved: uniform section-specific SCT v2, common minimum-section-median depth, log1p corrected counts and one section/type/gene centering operation. |
| Preflights | Canonical Python raw-input audit accepted: 432,794 eligible cells, 300 unique genes, no exclusions/invalid counts, all 19 section/glial totals matched, full-data depth 124 (S00__Trem2_5xFAD4). See the [accepted audit](docs/preprocessing/audits/20261030_raw/summary.md) and [preflight guide](docs/preprocessing/RAW_INPUT_PREFLIGHT.md). |
| Environment | Feasibility gate accepted with explicit glmGamPoi 1.25.1 development to 1.22.0 release amendment. Frozen target: R 4.5.3, Bioconductor 3.22, Seurat/SeuratObject 5.4.0, sctransform 0.4.3, Matrix 1.7-4. Local user-owned Windows environment materialized with real dependency/source locks; synthetic and S00 checks accepted. Future Linux verification container; no HPC normalization job approved. See the [specification](environment/sctransform/environment-spec.json) and [feasibility evidence](docs/environment/SCTRANSFORM_ENVIRONMENT_FEASIBILITY.md). |
| All-section input readiness | [Measured audit](docs/preprocessing/audits/20261031_readiness/README.md): all 5,700 section/gene combinations pass min_cells=5; all 19 input metadata/count contracts pass. This is input eligibility, not fitted-output certification. |
| Spatial holdout | Full-data production artifacts are not eligible for primary holdout scoring. Training-only preprocessing is required; fold-specific implementation design remains pending. |
| Bounded canonical normalization | New canonical validation runner passed deterministic synthetic fits and S00 at depth 124 using all 20,719 cells and 300 genes. Effective method, actual fitting cells and exact log1p layer equality verified. This bounded gate was followed by the separately approved all-19 v2 production run below. GP initialization has not run. See the [validation evidence](docs/preprocessing/audits/20261031_sct_smoke/summary.md). |
| Canonical response handoff | Approved [decision](docs/decisions/MODELING_RESPONSE_HANDOFF.md), [ordered 91-gene registry](config/preprocessing/modeling-panel.json) and [bundle specification](config/preprocessing/response-bundle.json). Metadata audit confirms 19 sections, 15 recorded animal labels and 187,100 selected glial cells. Coordinates remain unchanged in center_y/center_x order with source_native units; verified microns are not claimed. Amended single-section runner/validator passes S00 equivalence and isolated six-file validation with original attempt logs unavailable. Embedded execution evidence removes the external-log dependency. The single-section implementation, independent validation, S00 equivalence and six-file portability are accepted. Both S00 bundles remain review evidence generated from uncommitted code, not future all-section artifacts. The sequential all-section orchestration implementation and tests are accepted, with clean-commit provenance, durable resume, resource gates and bounded cleanup. The approved first real run promoted S00, then stopped on an over-strict S01 mean-validation check. The failed v1 root is immutable. The accepted [roundoff-aware validator correction](docs/preprocessing/MEAN_ROUNDOFF_VALIDATION.md) generated successful v2 production at commit `6eb672bebbaf5cde6c9d50391aac275a210832a6`. All 19 sections were recomputed from raw counts, with no v1 artifact reuse; all six-file bundles passed deep and closure integrity validation. See the [production receipt](docs/preprocessing/audits/20261031_production_v2/README.md). See the [orchestration design](docs/preprocessing/PRODUCTION_ORCHESTRATION.md). Attempt directories are optional debugging evidence. See the [runner guide](docs/preprocessing/SINGLE_SECTION_RESPONSE.md) and [review report](docs/preprocessing/audits/20261031_response_S00/summary.md). In failed v1, S01 was not promoted and the remaining 17 sections did not start. V1 remains immutable; v2 is a separate complete full-data run. |

All recovered writers export Seurat SCT `data`, the intended
`log1p(corrected counts)` representation. Ten new and three regional reused
scripts explicitly request SCT v2; six sct_work scripts depend on unpinned
historical defaults. Only the ten new sections have recovered normalization
session/completion records. Full-section input does not establish the internal
parameter-fitting cell subset. Correction depth was not harmonized; uniform
comparability is not certified. No evidence proves the historical procedures
wrong, and no historical implementation has been selected as authoritative.

The [19-section recipe ledger](docs/recovery/SCTRANSFORM_B6_SECTION_RECIPES.csv)
separates source behavior, runtime evidence, attribution and downstream adoption.
The approved design regenerates all 19 sections using all valid section cells
and the complete 300-gene panel, requires the effective glmGamPoi_offset method,
and uses correct_counts at the common minimum authenticated section median.
The full-data depth 124 is now accepted from the canonical raw-input audit.
MIC/AST/OGC and the fixed 91 genes are
selected after correction; the final response is centered once without variance
scaling. Residual-only settings do not define that response. The environment
decision deliberately amends the historical development dependency; it does
not claim exact historical reconstruction. Further substitutions require an
explicit version amendment. The [local build](docs/environment/SCTRANSFORM_ENVIRONMENT_BUILD.md)
now has actual dependency/source locks and bounded validation evidence. A
namespace-loading diagnostic warning remains documented; it did not occur in
the tested normalization path. All-19 full-data regeneration and canonical
response preparation have now passed production validation; training-only holdout
preprocessing remains pending. See the decisions for environment and holdout limits.

Accepted raw-source identity: SHA-256
`d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`,
5,483,600,151 bytes. This is a project-adopted content fingerprint, not an
independently supplied upstream checksum. The accepted 124 is the full-data
minimum-median depth, not automatically the training-only holdout depth.

- Accept raw gene-expression counts and spatial/cell metadata.
- Run SCTransform reproducibly.
- Use the recovered scientific response intent, `log1p(corrected counts)`, while
  distinguishing it from unverified historical normalization behavior.
- Preserve cell and gene identities, ordering, package versions, transformation
  settings, and fitted transformation state.

## 2. Spatial-GP factor initialization

The established C3 GP-smooth-to-SVD builder is the accepted canonical
[cold-start initializer](docs/initialization/C3_GP_SVD.md). Thirteen focused tests
pass. The user accepted S10 as numerically equivalent, explicitly not byte-exact,
under the [historical regression criterion](config/initialization/historical-regression.json).
The original strict loading/eta failures remain unchanged in the audit.
Same-environment determinism and saved readback still require exact equality.
GPINIT supplies starting values, not the posterior target; Lam/eta are
gauge-dependent coordinates and MCMC correctness must not depend on historical
seed bits. No all-section run is claimed. K and nfit remain explicit arguments;
no universal factor count is selected. The isolated
[GP environment](environment/gpinit/README.md) leaves accepted mesh/SCT environments
unchanged. GPINIT exports cold-start seeds only; it does not replace modeling Y.

- Fit a spatial GP to each transformed gene.
- Construct spatially smoothed gene surfaces.
- Use the established spatial-surface/SVD method to initialize the factor model.
- Preserve seeds, scaling conventions, dimensions, and reconstruction evidence.
- For held-out prediction studies, prevent held-out expression from entering
  initialization.

## 3. Adaptive tissue meshes

The mesh is a parsimonious basis for an unknown latent spatial warp. Production
selection must support smooth, learnable deformation and practical repeated
sampling, not reproduce an infinite-domain covariance across extreme prior ranges.
The [user scope reset](docs/decisions/ADAPTIVE_MESH_WARP_BASIS.md) selects the
October 26 four-stage fmesher builder as the **canonical practical mesh
implementation**, accepted by the user after the corrected S10 reproduction.
The sole canonical mesh entry point is `bsfm.mesh.october26.build`, configured by
[`october26-warp-basis.json`](config/mesh/october26-warp-basis.json). The module CLI
is only the bounded historical regression, not a second construction path.

Historical M1/M2 recovery is preserved. M3/Phase-0 is a **rejected experimental
redesign**; its v1/v2 failures are preserved in a
[concise historical receipt](docs/mesh/REJECTED_PHASE0.md), with the former source
and detailed study audits in Git history. Its launcher/configuration/schema/test
surface has been removed. Do not run
Phase-0 v3 or use its continuum grid to select production resolution.

The [canonical builder and computational-role report](docs/mesh/OCTOBER26_CANONICALIZATION.md)
recovers the mesh-to-warp-to-factor-GP handoff. It preserves full-glial geometry,
per-section glial normalization, inherited far boundary, four stages, 25-degree
angle request, consistent FEM and exact active marginalization. The first S10
regression exposed an R argument-type defect: JSON integer 25 silently left the
fmesher native 21-degree angle default active. The single corrected rerun used
explicit double 25 and **passed historical reproduction**: vertices, triangles,
projector and mesh RDS are byte-identical; FEM and marginalization checks pass.
See the [bounded localization](docs/mesh/audits/october26_S10_localization_20261102/README.md).
The resulting 371/708 counts are regression evidence, not scientific production
requirements. Outward coarsening, coverage and practical warp dimension matter.

The canonical mesh implementation has passed bounded S10 reproduction and is
canonicalized at commit `4f732ad08983e0b24aaba9fd99cabc1437e3c98a`. Outward grading and exact inactive-vertex
marginalization are load-bearing. No all-section mesh execution is claimed.
No sampler has been ported or run. No GP initialization, holdout,
resolution sweep, Phase 1 or HPC work is authorized by this gate. Physical units
remain source_native; no verified-micron claim is made.

The isolated [mesh environment](docs/environment/MESH_ENVIRONMENT_BUILD.md) and
[offline restoration](docs/environment/MESH_ENVIRONMENT_RESTORATION.md) remain
accepted environment evidence, not proof of reproducing the historical mesher
runtime by themselves. Canonicalization checks passed: **127 Python tests with
mesh/R integration enabled and seven R validation cases**. This includes the
permanent actual Python/JSON/R angle-boundary regression and its rejected
missing-conversion mutant. See the [acceptance record](docs/mesh/audits/october26_acceptance_20261102/README.md).

The subsequent [active-code cleanup](docs/mesh/audits/active_cleanup_20261102/README.md)
retains the canonical builder and reusable numerical dependencies unchanged,
removes rejected-study-only tests, and preserves 14 reusable numerical/resource
tests. Its complete suite passes 104 Python tests (including R/fmesher integration,
no skips) and seven R validation cases. The earlier 127-test count describes the
pre-cleanup acceptance checkpoint, not the remaining test inventory.

## 4. Bayesian spatial factor model sampler

Bounded recovery and nomination are complete. The user selected the
**F/C production-overlay direct-W/split-E architecture** for conservative porting;
the first Gaussian/shrinkage/PX layer is now implemented and validated, while the full
sampler remains unported. See the [layer-1 report](docs/sampler/LAYER1.md) and
[seven-function source map](docs/sampler/LAYER1_SOURCE_MAP.csv). Three bounded
synthetic source/port fixtures agree exactly, including both RNG streams; 27
focused tests pass. No historical monolith or experimental branch was imported,
and no full sampler/environment/run capability is claimed.
The deterministic full-spectrum warp/active-marginalization layer is now
implemented and validated: [layer-2 report](docs/sampler/LAYER2.md),
[source map](docs/sampler/LAYER2_SOURCE_MAP.csv), and
[isolated CPU environment](environment/sampler-layer2/README.md).
Two synthetic historical-reference comparisons and both S10 observation
populations match exactly in the pinned CPU environment; 22 focused layer-2
tests pass. This does not establish a GPU environment or complete sampler.
Layer 3's frozen L16 finite-feature likelihood, current-state statistics,
single-factor eta draw and direct-W target are **implemented and validated**:
[layer-3 report](docs/sampler/LAYER3.md),
[source map](docs/sampler/LAYER3_SOURCE_MAP.csv) and
[S10 mechanical smoke](docs/sampler/LAYER3_S10_SMOKE.json).
Two same-environment historical fixtures match exactly, including all gradients
and RNG states; 21 focused tests and all 49 prior sampler tests pass. S10 uses
synthetic response/state with authenticated geometry, not a fitted model.
The existing CPU environment is reused; no full sampler or GPU capability follows.
See the
[architecture decision](docs/decisions/BSFM_SAMPLER_ARCHITECTURE.md),
[model, chronology and evidence limits](docs/recovery/BSFM_SAMPLER.md), and
[source/dependency identities](docs/recovery/BSFM_SAMPLER_SOURCES.csv).
The decision preserves full-spectrum active marginalization, coupled warp
hypers, three conjugate subcycles, shrinkage/PX, factor chronology and complete
atomic restart state with explicit readaptation support. LI-ESS/Fisher/LI-NUTS
remain experimental and noncanonical; no unrecovered performance claim is made.
Only the six used functions from the large conjugate helper may be extracted;
the port must use small modules rather than copy the historical monolith.
K, chain count and run lengths remain open. Historical wrappers are not canonical.
No completed/converged F campaign, new sampler environment or HPC run is claimed.

- Implement the intended deep spatial factor model and priors.
- Implement its Gibbs schedule, including conjugate and NUTS updates.
- Preserve the correct partial-collapse/update chronology.
- Support exact inactive-vertex marginalization.
- Define initialization, adaptation, checkpointing, restarting, diagnostics, and
  retained posterior state.
- Determine saving frequency from the downstream scientific requirements while
  always retaining sufficient restart and diagnostic information.

## 5. Posterior reconstruction and visualization

- Plot factor paint at original tissue locations.
- Plot factor paint at warped tissue locations.
- Plot deformation/warp fields.
- Plot loading matrices using a scientifically meaningful amplitude convention.
- Compare observed expression with fitted expression.
- Plot expression and factor surfaces.
- Construct covariance matrices for selected cells and genes.
- Plot spatial covariance decay from an anchor cell for selected gene pairs.
- Render cells below the agreed covariance threshold in gray to avoid misleading
  visual emphasis.
- Display posterior uncertainty where scientifically relevant.

## 6. Integrated sender-cell covariance

- Define and calculate the covariance contribution summed/integrated over sender
  cells or sender regions.
- Construct cell footprints using high-resolution cell-centered polygons
  (historically discussed as 128-sided polygons), union them as appropriate, and
  intersect them with mesh triangles for integration.
- Recover the exact intended measure, overlap convention, and grouping rules.
- Provide posterior summaries and plotting functionality.

## 7. Wasserstein analysis

- Recover the exact scientific object and question being compared.
- Determine whether the calculation concerns covariance matrices, Gaussian
  distributions, spatial covariance operators, or integrated regional objects.
- Audit possible confounding by geometry, cell density, cell-type composition,
  gene set, scale, noise, subset selection, and posterior uncertainty.
- Determine whether polygon/mesh integration is actually part of this analysis.

## 8. Matched random covariance matrices

- Repeatedly select matched sets containing the same number of genes and cells.
- Support sampling from specified cell groups.
- Construct posterior covariance matrices of identical dimension.
- Calculate summaries such as the standard deviation of eigenvalues.
- Compare tissues while separating posterior uncertainty, cell-sampling
  variation, geometry, and composition.

## 9. Spatial-hole prediction

- Generate reproducible tissue holes with varying sizes and counts.
- Remove the corresponding cells from fitting.
- Determine which preprocessing steps must be repeated per fold.
- Recompute GP initialization without held-out expression when required.
- Fit the deep model on remaining cells.
- Predict full posterior distributions at held-out spatial locations.
- Fit and predict with a matched flat spatial-factor GP without the warp layer.
- Score deep versus flat prediction with paired masks and agreed metrics.
- Explore hole designs without selecting and reporting a favorable configuration
  on the same data used for final evaluation.

## 10. Cross-cutting platform requirements

- Original-data and biological-unit provenance.
- Gene-panel construction and provenance.
- Simulation and known-truth recovery where appropriate.
- Factor sign, label, rotation, and cross-chain alignment handling.
- Posterior predictive checks and scientific convergence diagnostics.
- Reproducible environments and random-number management.
- Reliable, restartable HPC execution with one authoritative status ledger.
- Manifests connecting every scientific result to code, configuration, inputs,
  environment, and output artifacts.

## Status

The October 26 mesh construction is selected for conservative porting. Its first
reproduction failed; one localized argument-type correction then reproduced S10.
The corrected builder is accepted as the canonical practical mesh implementation.
The first canonical code is
the raw-input preflight, implemented from the frozen contract, tested and
accepted with the aggregate audit above. The SCT validation runner passed
synthetic checks and a bounded S00 smoke.
The subsequent canonical v2 production run recomputed and validated all 19
full-data section bundles; its [receipt](docs/preprocessing/audits/20261031_production_v2/README.md)
registers the external artifacts. Real S10 experimental mesh construction and
a historical-port regression ran; the first port attempt failed and its single
authorized corrected rerun passed. No GP/BSFM
model or HPC execution is included; no mesh was promoted to production.

