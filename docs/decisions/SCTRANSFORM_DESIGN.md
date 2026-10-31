# Canonical SCTransform preprocessing decision

Decision date: 2026-10-30.
Status: **scientific choices frozen by explicit user approval; canonical raw-input
preflight and full-data depth accepted; bounded SCT implementation validated on
synthetic data and S00, accepted; all-section execution pending**.
Evidence baseline: clean commit `8e84d872f57507d3b9937dca0e37083bbc3722f7`.
Preflight amendment: 2026-10-30, following implementation from design checkpoint
`909d86da682695279a456dca396a1e6b2e23b3b9` and explicit user acceptance.

This decision replaces the pending scientific design gate described at the end
of [historical recovery](../recovery/SCTRANSFORM_PREPROCESSING.md). The
[evidence ledger](../recovery/SCTRANSFORM_EVIDENCE.md) and
[19-section historical recipe table](../recovery/SCTRANSFORM_B6_SECTION_RECIPES.csv)
remain historical evidence. No legacy implementation is selected or imported.
The authority for the choices below is the user's acceptance of the design memo
with amendments, not a claim that the historical pipeline was scientifically wrong.

## 1. Frozen scientific choices

| Item | Approved choice |
| --- | --- |
| Regeneration | Regenerate all 19 registered sections uniformly. Do not mix newly generated responses with reused historical SCT CSVs. |
| Normalization unit | One independent SCT-v2 fit per tissue section; no joint fit and no common reference-model fit for the full-data analysis. |
| Input cells | All valid cells in each section, including nonglial cells. Exclude zero-total and structurally invalid cells and report their identities and reasons. |
| Additional QC | No additional expression-based cell exclusion or threshold without separate approval. Do not silently inherit undocumented historical filters. |
| Input genes | The complete authenticated 300-gene measured panel, before the fixed 91-gene modeling subset. No random gene subsampling. |
| Fitting cells | All eligible section cells participate in parameter estimation; merely supplying all cells while fitting a subset does not satisfy this choice. |
| SCT flavor | Explicit `vst.flavor="v2"`. |
| Effective method | Require glmGamPoi; assert the fitted model records `glmGamPoi_offset`. This is the effective method selected by v2, not an independently competing method argument. Missing dependency or fallback is a failure. |
| Feature retention option | Explicit `return.only.var.genes=FALSE`. |
| Covariates | Depth adjustment only. No biological, genotype, spatial or cell-type covariates regressed out. |
| Common depth | Minimum authenticated section median of raw counts summed across the full measured panel, using the final eligible cell population. |
| Final correction | Canonical final corrected counts from `sctransform::correct_counts`, with the common depth supplied explicitly. |
| Uncentered response | Exactly one natural `log1p` of the common-depth corrected counts. |
| Modeling selection | Select MIC/AST/OGC and the fixed, ordered 91 genes after correction. |
| BSFM preparation | Center once within section, cell type and gene, using the actual modeled cells. No variance scaling. |
| Preservation | Retain corrected counts, uncentered response, centered response, centering means and identities. |
| Primary spatial validation | Training-only preprocessing; held-out expression cannot affect fitting or preprocessing estimates. |
| Secondary validation | Full-data-preprocessed field interpolation, explicitly labeled secondary/transductive. |

The 300-gene choice defines the normalization input and depth denominator. It
does not claim that every gene is statistically estimable in every section or
fold. SCT has gene eligibility and regularization rules; its v2 implementation
also distinguishes Poisson-like genes. Preserve effective rules, eligible genes
and model parameters. A missing required 91-gene model must be reported as a
contract failure, not silently filled with zeros or dropped. These gene rules
must not become unapproved additional cell-QC exclusions.
[sctransform 0.4.3 fitting source](https://github.com/satijalab/sctransform/blob/v0.4.3/R/vst.R).

Historically, B6 recovered ten new, three regional reused and six sct_work reused
section recipes. All writers exported SCT data, but only thirteen section-linked
recipes explicitly requested v2; six depended on unpinned defaults. Correction
depth was not harmonized. Uniform regeneration removes those recipe
ambiguities. It does not by itself certify biological comparability.

## 2. Common correction-depth definition

Let G300 be the authenticated measured panel and I_s the final eligible cells
of section s. Define from raw counts X:

```text
d[s,i] = sum(X[s,g,i] for g in G300)
m[s]   = median(d[s,i] for i in I_s)
D      = min(m[s] for s in the fixed 19-section registry)
```

All section medians must be computed on the same measured gene universe. Do not
recalculate depth after selecting the 91 genes, glia, or modeling-cell subsets.
Record all 19 medians, the eligible populations, the minimizing section(s), the
median convention, numeric precision and resulting D. Reject missing sections
or invalid depth summaries rather than changing the denominator silently.

**The authenticated full-data depth is now frozen at D = 124** for the accepted
source fingerprint and eligible population recorded in section 5. The canonical
preflight recomputed all 19 medians, ranging from 124 to 387, and identified
S00__Trem2_5xFAD4 as the minimizing section. This agrees with the earlier
historical provisional value. The rule remains computed from raw counts; the
preflight does not hardcode 124. A changed source or population requires a new
audit and review. This full-data depth is not automatically a training-only
holdout depth.

Seurat documents minimum-median recorrection for independently fitted SCT models,
with corrected counts and their log1p stored in counts and data. The convention
is supported by the v2 paper's cross-dataset corrected-count comparison.
[PrepSCTFindMarkers](https://satijalab.org/seurat/reference/prepsctfindmarkers),
[Choudhary and Satija, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC8764781/).

The approved implementation route is the exported correct_counts function,
applied to raw counts and fitted model parameters with scale_factor=D. Its
rounding and nonnegative truncation belong to the corrected-count definition.
Do not replace this with proportional rescaling of an existing corrected matrix
or an operation on already logarithmic values. This is also the correction
routine used by Seurat's multiple-model preparation.
[sctransform correction source](https://github.com/satijalab/sctransform/blob/v0.4.3/R/denoise.R),
[Seurat 5.4.0 recorrection source](https://github.com/satijalab/seurat/blob/v5.4.0/R/differential_expression.R).

For this targeted assay, D is a measured-panel count-depth covariate, not a
measurement of total cellular RNA or a requirement that corrected column sums
equal D. The scientific choice is to standardize this covariate across sections.
Gene/cell composition and section-specific fitted parameters can still differ.
No claim of absolute RNA abundance or empirically established comparability is
made by adopting a common depth.

Centering cannot generally remove a depth change: even a pure multiplication c
to a*c changes log(1+c) by log(1+a*c)-log(1+c), which depends on c. This is a
mathematical deduction explaining why centering is not a substitute for the
approved common-depth correction.

## 3. Response and handoff invariants

The authoritative transformation is:

```text
authenticated raw counts + section/cell/gene identities
  -> explicit eligibility (all cell types; complete 300-gene panel)
  -> independent section SCT-v2 fit using every eligible cell
  -> correct_counts(raw counts, fitted section model, common D)
  -> C: corrected counts
  -> L = log1p(C): uncentered response
  -> MIC/AST/OGC and ordered 91-gene selection
  -> any separately approved modeling-cell selection
  -> subtract saved section/type/gene means once
  -> Y: centered response supplied identically to GPINIT and BSFM
```

The implementation must establish these invariants before accepting an export:

1. Exactly the approved 19 section identities; stable unique cell/gene IDs and
   explicit orientation. Export expression as genes x cells and preserve both
   ordered identifier arrays.
2. Valid raw counts and aligned metadata. Report structurally invalid or zero-total
   cells; do not silently round fractional input or invent expression-QC cutoffs.
   Dataset-wide identity/axis corruption is a preflight failure, not permission
   to discard arbitrary data.
3. Every eligible fitting-cell ID is represented in the recorded fitting set.
   Explicit ncells=N_eligible and no gene subsampling must be checked against
   effective arguments/model records, not inferred from the call alone.
4. glmGamPoi is present and the recorded effective method is glmGamPoi_offset.
   In the inspected versions, Seurat passes an explicit cell count into vst,
   while v2 selects the offset method and can otherwise fall back. Verify these
   behaviors in the frozen environment.
   [Seurat 5.4.0 wrapper](https://github.com/satijalab/seurat/blob/v5.4.0/R/preprocessing.R),
   [sctransform 0.4.3 fitting source](https://github.com/satijalab/sctransform/blob/v0.4.3/R/vst.R).
5. Raw counts remain separately identified (input assay RNA/counts); final
   SCT/counts contains C at the approved common depth, and SCT/data contains L.
   The official Seurat contract identifies data as log1p of corrected counts.
   Verify the numerical equality rather than trusting an assay label.
   [SCTransform reference](https://satijalab.org/seurat/reference/sctransform).
6. No second log1p in the exporter, GPINIT or sampler. Replacing data with
   log1p of newly recorrected counts is not applying log1p to the previous data.
7. No silent zero-fill or gene deletion for an unavailable modeled gene. Retain
   explicit detection/model availability and fail the fixed-panel contract if
   it cannot be fulfilled.
8. For each retained section s, type t and gene g, save
   mean[s,t,g] = mean(L[s,g,i] over actual modeled cells i of type t).
   Set Y[s,g,i] = L[s,g,i] - mean[s,t,g]. Save group sizes, ordered cell IDs and
   numerical centering residuals. No division by standard deviation occurs.
9. Preserve L independently of Y. Cell selection precedes final centering.
   Historical every-other-cell thinning is not implicitly adopted. Any later
   subset produces a separately identified response/means artifact, not an
   undocumented in-place recentering.
10. GPINIT and the sampler consume the same immutable final Y with matching
    dimensions, identities, order and hash. Downstream code must not add a
    response transformation; verification may check means without changing Y.

Centering intentionally removes section/type gene means from Y. Those means and
L remain available for reconstruction and analyses whose target includes means.
This algebraic property is distinct from approval of any later scientific analysis.

## 4. Residual settings and implementation reproducibility

SCT scale.data is not the modeled response. Residual centering, residual scaling
and residual clipping are outside the scientific definition of L and Y. Record
their effective values and the dispatch path for reproducibility, but do not
apply those operations to C, L or the final Y. Seurat documents these parameters
as residual operations.
[SCTransform reference](https://satijalab.org/seurat/reference/sctransform).

The final correction must use raw counts and fitted parameters through
correct_counts, not a clipped/centered scale.data matrix. Initial correction
and recorrection are distinct code paths; do not assume their numerical outputs
are interchangeable. The canonical final path is fixed here.
[sctransform correction source](https://github.com/satijalab/sctransform/blob/v0.4.3/R/denoise.R).

The implementation specification must record all effective fit/filtering defaults,
including gene eligibility, regularization, Poisson handling, variance-floor
settings, seeds/RNG, numerical-library threads and input ordering. The memo's
seed 1448145 and gene min_cells=5 are initial implementation targets, not new
expression-based cell-QC rules. Runtime arguments and realized fitting populations
must be preserved. Residual settings must not be used to redefine the response.
No claim of numerical reproducibility across untested platforms is made here.

## 5. Provisional values and required preflights

### Raw-source identity and depth preflight

The canonical preflight has been run read-only and accepted for
`D:\johnston_brain\Johnston_MERFISH_Data.h5ad`, `layers/RNA`.
The path records this acquisition location; callers supply their input path.
See the [accepted aggregate audit](../preprocessing/audits/20261030_raw/summary.md),
[manifest](../preprocessing/audits/20261030_raw/manifest.json) and
[19-section table](../preprocessing/audits/20261030_raw/sections.csv).

| Accepted property | Measured result |
| --- | --- |
| Source SHA-256 | `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38` |
| Source byte size | 5,483,600,151 |
| Eligible cells | 432,794, covering all 19 frozen section selections, including both S12 sections |
| Measured genes | Exactly 300 unique genes; gene and cell order fingerprints recorded |
| Input validation | All counts finite, nonnegative and integer-valued; unique cell IDs; required section/type/spatial metadata valid |
| Exclusions | Zero invalid or zero-total cells; no exclusions |
| Historical comparison | All 19 section totals and MIC/AST/OGC totals matched B6; 187,100 glial cells overall |
| Full-data common correction depth | 124, minimum of the 19 authenticated section medians |
| Minimizing section | S00__Trem2_5xFAD4 |

This is a **project-adopted content fingerprint**, accepted by explicit user
decision after contract validation. It is not an independently supplied upstream
checksum or proof of original acquisition authenticity. No independent ordered
gene reference was supplied. The fixed 91-gene modeling list and gene-model
availability remain later checks. No SCTransform response has been generated
or certified by this audit.

The optional B6 ledger is a cross-check only. Eligibility and depth depend on
the frozen registry and raw input, never on historical target counts. The
accepted aggregate records include the absolute interpreter, dependency versions,
exact CLI argument vector, and final module/registry hashes. Full audit and
exclusion artifacts remain outside Git at the invocation's output directory.

Any new expression-based exclusion requires separate scientific approval.
Changed source identities or eligibility populations require a new audit; do
not change the panel or normalization rule to make a check pass. The value 124
applies to the full-data population above and must not be inherited silently
by training-only spatial holdout preprocessing.

### Accepted environment feasibility gate and version amendment

The [canonical environment decision](SCTRANSFORM_ENVIRONMENT.md) now freezes
the following build target after the feasibility gate and explicit user approval:

| Component | Frozen version |
| --- | --- |
| R | 4.5.3 |
| Bioconductor | 3.22 |
| Seurat | 5.4.0 |
| sctransform | 0.4.3 |
| Matrix | 1.7-4 |
| SeuratObject | 5.4.0 |
| glmGamPoi | 1.22.0 |

This deliberately replaces the historically recorded glmGamPoi 1.25.1
development target with released 1.22.0. It is not an exact historical
reconstruction or a claim of numerical equivalence. Historical session records
remain unchanged. See the [feasibility evidence](../environment/SCTRANSFORM_ENVIRONMENT_FEASIBILITY.md)
for established source identities and remaining acquisition/build gaps.

Initial execution targets an isolated, user-owned local Windows environment,
with a real renv lock, immutable source/binary hashes and exact session/build
records. Add a Linux verification container after the local source-locked
environment works. Current HPC container compatibility is unresolved and no
HPC normalization job is approved. Acquisition, installation and validation
were separate future steps at that decision. They were subsequently authorized
and completed for the bounded local validation; see the linked build evidence.
The environment decision defines the required method, fitting-population,
determinism, layer-equality, common-depth correction and bounded S00 checks.

### Artifact requirements

Keep large data and model artifacts outside Git. Track their schemas, exact
locations, byte sizes and hashes in manifests. Retain:

- Authenticated raw-source identity, extraction schema/key, ordered genes/cells,
  section/type mappings, eligibility masks and exclusion reasons.
- Fitted SCT models and the parameters/attributes needed for correct_counts;
  effective arguments, fitting-cell identities and gene eligibility/outliers.
- Raw panel depths, 19 medians, common D and its derivation population.
- C, L, final Y, centering means/group sizes and availability metadata.
- Source Git commit, frozen configuration, lockfile/container identity, session
  information, seeds, commands, warnings, exit status and output identities.
- Contracts linking each response to GPINIT and BSFM by dimensions, ordering and
  hashes; execution evidence must remain distinct from configured commands.

## 6. Frozen validation policy and later holdout implementation design

The primary policy is training-only preprocessing. For each spatial holdout,
held-out expression must not influence SCT parameters, normalization populations,
depth selection, centering means, GP initialization or model fitting. Full-data
preprocessing followed by a response mask is a different, secondary/transductive
benchmark. Data-dependent preprocessing can bias cross-validation; spatial split
design must match the intended prediction task.
[Moscovich and Rosset, 2022](https://arxiv.org/abs/1901.08974),
[Roberts et al., 2017](https://florianhartig.github.io/publications/roberts2017cross/).

The policy applies to all cell types inside a held-out region, not just glia.
Depth summaries for the primary policy must use training data only, or a genuinely
independent reference approved in the holdout specification. The full-data D,
including the accepted full-data value 124, cannot silently enter that policy.
Use training centering means for both training responses and held-out scoring.

After predictions are fixed, held-out raw observations may be transformed with
the frozen training model/common training depth to construct scoring targets.
They cannot feed back into the predictor. This evaluates corrected-expression
prediction, not automatically a predictive distribution for unseen raw counts.
A raw-count prediction claim requires a separately designed observation/depth
model; expm1 alone does not undo model-based correction and rounding.

The following details are **not frozen by this decision** and require a separate
holdout implementation specification before running validation:

- Spatial masks, buffers, folds, section/animal grouping and permitted geometry.
- Exact fold-wise population/depth aggregation and cross-fold score reporting.
- Frozen-model application and correction for held-out cells, with no query
  refitting or query-dependent parameter updates. Seurat's reference-model
  shortcut disables corrected-UMI generation in the inspected wrapper; it is
  not by itself the required response transformation.
  [Seurat 5.4.0 reference path](https://github.com/satijalab/seurat/blob/v5.4.0/R/preprocessing.R).
- Handling of training folds with unavailable genes or cell types; no silent
  use of held-out data to rescue a failed fit.
- Which cell-type labels and count-depth covariates would genuinely be available
  at prediction time, and which are used only to construct scoring targets.
- Metrics, predictive intervals and distinctions between fixed-panel evaluation
  and evaluation of gene selection. Freezing the historical panel now does not
  prove its selection was independent of held-out expression.
  [Ambroise and McLachlan, 2002](https://pubmed.ncbi.nlm.nih.gov/11983868/).

## 7. Decision boundary

The scientific choices above are authoritative repository decisions. Raw-input
preflight and full-data depth 124 are accepted for the recorded fingerprint.
The R environment specification is approved. The 2026-10-31 assignment authorized
acquisition, local build and bounded validation before commit; its
[results](../preprocessing/audits/20261031_sct_smoke/summary.md) are accepted by explicit user approval.
The Python preflight remains a raw-input audit; the separate canonical SCT
runner has passed synthetic and S00 checks. Remaining-section execution and
holdout implementation design remain pending. Future changes to frozen scientific choices require an
explicit decision amendment; historical findings remain preserved as evidence.
