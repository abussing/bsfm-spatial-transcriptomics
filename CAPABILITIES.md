# Required capability map

This is the initial user-authored functionality inventory. It records required
capabilities, not claims that any historical implementation is authoritative.

## 1. Expression preprocessing

Recovery status: **historical normalization-recipe recovery completed through
B6; canonical scientific design approved; implementation not begun**. See the
[canonical SCTransform decision](docs/decisions/SCTRANSFORM_DESIGN.md),
[SCTransform recovery](docs/recovery/SCTRANSFORM_PREPROCESSING.md) and
[evidence ledger](docs/recovery/SCTRANSFORM_EVIDENCE.md).

| Aspect | Status |
| --- | --- |
| Scientific response intent | Recovered: log1p(corrected counts). |
| Downstream exporter/handoff | Recovered: implemented behavior and recorded artifact links; actual sampler invocation is not certified. |
| Historical normalization implementation | Recovered writer recipes: 10 new, 3 regional reused, 6 sct_work reused; effective defaults/execution attribution remain incomplete. |
| Uniform cross-section comparability | Unestablished. |
| Replacement design | Approved: uniform section-specific SCT v2, common minimum-section-median depth, log1p corrected counts and one section/type/gene centering operation. |
| Preflights | Raw-source/eligibility/depth authentication and exact environment feasibility pending; numeric depth is not frozen. |
| Spatial holdout | Training-only preprocessing approved as primary policy; fold-specific implementation design remains pending. |

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
The historical depth 124 is provisional. MIC/AST/OGC and the fixed 91 genes are
selected after correction; the final response is centered once without variance
scaling. Residual-only settings do not define that response. The recovered
environment is an initial target subject to feasibility; substitutions require
an explicit version amendment. No preprocessing code or run is authorized by
the documentation checkpoint. See the decision for preflights and holdout limits.

- Accept raw gene-expression counts and spatial/cell metadata.
- Run SCTransform reproducibly.
- Use the recovered scientific response intent, `log1p(corrected counts)`, while
  distinguishing it from unverified historical normalization behavior.
- Preserve cell and gene identities, ordering, package versions, transformation
  settings, and fitted transformation state.

## 2. Spatial-GP factor initialization

- Fit a spatial GP to each transformed gene.
- Construct spatially smoothed gene surfaces.
- Use the established spatial-surface/SVD method to initialize the factor model.
- Preserve seeds, scaling conventions, dimensions, and reconstruction evidence.
- For held-out prediction studies, prevent held-out expression from entering
  initialization.

## 3. Adaptive tissue meshes

- Construct meshes from tissue cell locations using the adaptive method.
- Use multiple layers of resolution that become coarser outside the cell hull.
- Recover and document the settled refinement and outer-buffer choices.
- Construct and retain FEM matrices and projection operators.
- Support exact marginalization of outer/inactive mesh vertices.
- Provide numerical geometry checks and human-review plots.

## 4. Bayesian spatial factor model sampler

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

No implementation has yet been selected for any capability in this repository.

