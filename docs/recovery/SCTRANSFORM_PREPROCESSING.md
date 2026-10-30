# SCTransform preprocessing recovery through Stage B2

Checkpoint date: 2026-10-30. Status: **in progress**.

**No implementation has been selected.** Historical files are evidence, not
authoritative implementations. This checkpoint records the completed B1 metadata
and lineage review and B2 six-file source review. Later B3 work in the recovery
conversation is intentionally excluded; this is not a statement that B3 never
occurred. No legacy implementation is included in this repository.

## Stated scientific intent

The user's explicit decision is:

```text
raw gene counts -> SCTransform -> corrected counts
                -> log1p(corrected counts) -> GP initialization and BSFM
```

Recovery must identify the precise corrected-count object, Seurat assay/slot/layer,
SCTransform settings and versions, downstream transformations, and evidence of
actual consumption. An older residual-based candidate does not reopen this
response-scale decision. This decision supersedes the tentative wording in the
initial capability inventory. See evidence U1 in the [ledger](SCTRANSFORM_EVIDENCE.md).

## Evidence boundary and lineage

Aliases and exact paths are defined in the ledger. The four locations principally
represent one documented lineage:

```text
Z (ZIP listing) <-> E (base source handoff)
                       |
                       v
                   P (production overlay)
                       |
                       v
                   C/source_snapshot/code
```

The ZIP's 72 file entries have corresponding E files of matching sizes; byte
identity was not established. P explicitly identifies E as its base. C's recorded
bundle hashes match 70 of E's 71 base-manifest entries; the difference is the
declared driver revision. All 17 additions listed by P's overlay manifest agree
with C's bundle records. These are manifest comparisons, not independent
validation of three implementations. Only the six B2 source files were freshly
hashed. No historical program was executed in B1/B2 and no HPC was accessed in
those stages.

## Recovered transformation and handoff graph

File IDs A-F below refer to the six measured sources in the ledger. Line numbers
refer to those exact file versions. A dotted connection is still unverified.

```text
raw counts -> SCTransform -> corrected counts -> log1p
                  [upstream implementation and execution unresolved]
                                  ...
<screen-root>/sections/<section>/input.npz["Y"]
  -> A: panel gene selection; stable MIC/AST/OGC column ordering
  -> A: float64, genes x cells; within-type gene-mean subtraction
  -> <output>/sections/<section>/OBSERVATIONS_BASE.npz["Y"]
       |
       +-> C: production wrapper invokes an uninspected transfer builder
       |      ... -> OBSERVATIONS.npz -> D: GPINIT
       |
       ... -> consolidation source_geometry/<section>/OBSERVATIONS_BASE.npz
              -> B: retained-cell selection and within-type re-centering
              -> inputs/<section>/OBSERVATIONS.npz["Y"]
                         ... -> D: GPINIT

observation artifact -> D: Y copy and within-type centering -> GP inputs -> seeds
observation artifact -> E/F: Y loaded unchanged at input boundary
GPINIT artifact      -> E/F: seed loading and dimension checks
```

The historical observation/GPINIT pairing passed to the sampler is not established
by B2. The graph describes implemented operations and identified gaps, not a
verified end-to-end run.

| Transition | Exact implementation evidence |
| --- | --- |
| Upstream input | A:30-49 reads the panel, `audit/SECTIONS.csv`, and each section's `input.npz`; keys include `Y`, `raw`, `genes`, `types`, `available`, coordinates and identifiers. The actual `--screen-root` value is unresolved at this checkpoint. |
| Gene selection | A:34-56 selects the panel CSV's `gene` order and rejects missing/unavailable genes. |
| Cell order | A:14-15,58-80 maps `Mic`, `AST`, `OGC` to 0,1,2 and stably groups columns. It retains all cells in that section input and permutes identity metadata consistently. |
| Orientation and transformation | A:79-92 selects `Y[lookup][:, order]` as float64, genes x cells, and subtracts gene means within each type. It applies no response log transform or variance scaling. A:94-99 normalizes coordinates, not expression. |
| Base export | A:101-134 writes centered `Y`, ordered identities and `centering_means` to `OBSERVATIONS_BASE.npz`; a separate sidecar preserves incoming expression and raw counts. |
| Claimed upstream scale | A:148 writes the description `section-specific SCT v2 log1p, centered separately by gene and cell type`. This is a claim about the already-loaded input, not an SCTransform/log1p implementation. |
| Production transfer | C:15-27 invokes `build_section_mesh.py`, then passes `OBSERVATIONS.npz` to GPINIT. The transfer builder is outside B2; preservation of Y across it is unresolved here. |
| Consolidation input/selection | B:35-48 reads `source_geometry/<section>/OBSERVATIONS_BASE.npz` and selects every other cell in within-type Morton order; B:17-24 defines the ordering. Retained indices are then sorted. |
| Retained response | B:60-69 subsets Y columns and matching identities, subtracts retained within-type gene means, and adds those shifts to stored centering means. No new gene selection, response logarithm, or response variance scaling occurs. |
| Consolidation export | B:70-76 sets 20 factors and exports `inputs/<section>/OBSERVATIONS.npz` plus retained original indices. |
| GPINIT response | D:49-66 reads only `Y`, `slocs`, and `cell_id`, copies Y to float64, and subtracts within-type gene means over all supplied cells. |
| GP fitting inputs | D:79-96 selects at most `nfit` cells per type after centering, passes `y[g, fit]` to each GP, and requests `normalize_y=True`. Library normalization internals were not inspected. |
| Initialization outputs | D:120-132 centers predicted fields across output locations before SVD; D:167-177 exports loading/factor seeds and diagnostics, not replacement observation Y. |
| Sampler input | E:335-367 / F:330-362 loads Y as floating point and checks shape, finite values, nonempty types and contiguous type blocks. The inspected drivers contain no response-centering operation. |
| GPINIT compatibility | E:468-480 / F:463-475 loads `Lam_seed` and `eta_seed` and checks dimensions. It does not compare source hashes or ordered gene/cell identities at this boundary. |

## Centering findings

For one section, gene g, and cells I_c of cell type c, the operator is

```text
C(X)[g,i] = X[g,i] - mean(X[g,j] for j in I_c), i in I_c.
```

This is unweighted arithmetic-mean centering separately by gene and cell type
within a section. It is not centering across tissues or across genes.

| Stage | Cells used to calculate means |
| --- | --- |
| A: initial preparation | All source cells of the type in the current section. |
| B: retained-cell preparation | Only retained cells of that type. |
| D: GPINIT | All cells of that type in the supplied observation artifact, before GP fit-point subsampling. |
| E/F: sampler input | No mean subtraction. |

Let R select retained columns. In exact arithmetic,

```text
C_retained R C_full X = C_retained R X.
```

Subsetting and re-centering therefore generally changes the retained response,
but yields the same response as directly centering retained original expression.
Adding the retained shifts to stored centering means is consistent with this
identity. This is a narrow mathematical finding, not approval of the scientific
choice of centering groups or a demonstration that historical runs used this path.

Given the same observation artifact, the sampler loads Y while GPINIT uses C(Y).
They agree in exact arithmetic if Y already has zero within-type gene means.
Floating-point equality is not guaranteed; GPINIT removes residual numerical
means. With uncentered input the difference could be material. GP fitting uses
selected cells and normalization, and predicted-field centering affects seeds,
not the sampler response matrix.

A:91-92 checks residual means against 2e-12; B:68 uses an assertion at that
tolerance. D:61-66,197 records `maximum_input_recentering_mean`. B2 inspected the
checks and reporting code, not their historical measured values. Assertions can
be disabled in optimized Python. No numerical run or array comparison was made.

## Defaults, configured commands, and historical records

| Setting | Default or implementation | Command/configuration evidence | Execution limit |
| --- | --- | --- | --- |
| Base preparation | A:178-181 requires screen/panel/output paths; factors default to 5. | Historical invocation not recovered. | Neither actual paths nor factor override established by this source alone. |
| Retained preparation | B:46-48,70 hardcodes every-other-cell selection within type and 20 factors. | B1 input manifest records 19 sections, 91 genes, 20 factors and that selection. | Matching descriptions do not independently prove which source bytes ran. |
| GPINIT | D:211-213 defaults to 5 factors, nfit=500, seed=0. | C:17,23-27 reads factors from the base artifact, overrides nfit=250 and seed=2026102400 + task ID. | A wrapper is evidence of configured commands, not proof of invocation. |
| Sampler | E:1715-1721 / F:1684-1690 requires observation and GPINIT paths; real-data mode is opt-in. | B1's recorded base command references a simulation case. | The production command and paired input artifacts remain unverified. |

## Provisional conclusions and contradictions

1. The inspected downstream centering sequence is mathematically coherent under
   the stated grouping and artifact assumptions. No preprocessing error follows
   merely from repeated references to centering.
2. The inherited model note says the driver centers Y. D:60 also says its centering
   reproduces the runner. Neither inspected driver contains that operation.
   These documentation/comment claims conflict with the inspected code versions.
3. A's SCT-v2-log1p contract string does not establish the upstream implementation
   or the precise meaning of corrected counts.
4. P and C retain the original base manifest while overlay/bundle metadata record
   a changed driver. The base manifest alone is not a complete later snapshot.
5. The overlay README describes only a retention extension, while its manifest
   also describes checkpoint re-adaptation. This is a documentation discrepancy;
   it is not evidence of a response-scale change.
6. B1's local package result reports CPU validation and GPINIT success, while input
   records retain `EXPORTED_AWAITING_SAMPLER_VALIDATION`. These may describe
   successive stages. Their underlying certificates were not read through B2.
7. Shape-compatible GPINIT is not proof of matching values or cell/gene order.
   End-to-end historical consumption remains unresolved.

## Unresolved upstream provenance and next evidence

Through B2, no actual SCTransform invocation, upstream R script, RDS/Seurat
object, or export implementation has been identified. The remaining questions
include assay/slot/layer, corrected-count definition, v2 settings, package versions,
per-section versus pooled fitting, raw-input provenance, gene availability,
log1p placement, and evidence that these operations ran before input export.

The bounded follow-up identified by B2 consists of the production builder's
observation-transfer statements, consolidation preparation/launch wrappers, and
named input contracts and GPINIT certificates under the two HPC roots listed in
the ledger. They are follow-up references, not B1/B2-inspected sources. Later-stage
findings must be added in a separate checkpoint with their own evidence boundary.

No implementation is selected, imported, certified, or approved for execution by
this recovery checkpoint.
