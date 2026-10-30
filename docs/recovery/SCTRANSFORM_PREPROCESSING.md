# SCTransform preprocessing recovery through Stage B4

Checkpoint date: 2026-10-30. Status: **in progress**.

**No implementation has been selected.** Historical files are evidence, not
authoritative implementations. B1/B2 are preserved at commit
`d2e7e5ea9db420fe2910cd54ac1e33040a0726db`; B3 is preserved at
`71a7dcad7a2252157c7cd8e83bfb4bdd9a6b3b7a`. This increment records the accepted,
incomplete B4 upstream exporter recovery. Earlier-stage sections retain their
historical evidence boundaries. No HPC reconnection or historical scientific
execution was used to prepare this checkpoint. B5 has not begun.

**Certification remains incomplete:** `review.py` does not itself implement
SCTransform. Its `sct_section.R` dependency is missing from the inspected package.
Readiness records can reuse preexisting CSVs. Nine reused historical exports have
separate unrecovered normalization implementations; ten sections are recorded as
newly normalized. Comparability across these two branches is not established,
and correction depths were explicitly not harmonized. **`log1p(corrected counts)`
is the scientific intent, not yet a certified fact about every historical section.**

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

## B1/B2 transformation and handoff graph

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
| Upstream input | A:30-49 reads the panel, `audit/SECTIONS.csv`, and each section's `input.npz`; keys include `Y`, `raw`, `genes`, `types`, `available`, coordinates and identifiers. The screen root was unresolved through B2; B3 recovers the effective root from recorded source paths below. |
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

## B1/B2 provisional conclusions and contradictions

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

## B2 stopping point

Through B2, no actual SCTransform invocation, upstream R script, RDS/Seurat
object, or export implementation has been identified. The remaining questions
include assay/slot/layer, corrected-count definition, v2 settings, package versions,
per-section versus pooled fitting, raw-input provenance, gene availability,
log1p placement, and evidence that these operations ran before input export.

The bounded follow-up identified by B2 consists of the production builder's
observation-transfer statements, consolidation preparation/launch wrappers, and
named input contracts and GPINIT certificates under the two HPC roots listed in
the ledger. They were follow-up references, not B1/B2-inspected sources. The B3
increment below records their subsequent inspection and its limits.

No implementation is selected, imported, certified, or approved for execution by
this recovery checkpoint.

## B3 accepted increment

The user accepted the concrete B3 report and requested this separate checkpoint.
This is an audit of recorded preparation-to-GPINIT relationships, not a new
scientific run or a certification of response scale. Acquisition and validation
details are in the [B3 evidence ledger](SCTRANSFORM_EVIDENCE.md#b3-capture-preservation-and-validation).
The [19-section CSV](SCTRANSFORM_B3_SECTIONS.csv) retains exact paths, hashes,
dimensions, residuals and match flags.

### Updated artifact lineage

H-P and H-C are the HPC roots defined in the ledger. B3 discovered the effective
upstream root H-U:

`/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1`

All 19 production contracts name exactly
`H-U/sections/<section_id>/input.npz`, using the section IDs in the CSV.
This recovers the effective source family from recorded paths; the literal
historical `--screen-root` command was not recovered. H-U was not opened.

| Boundary | B3 evidence and limit |
| --- | --- |
| H-U input to H-P base observations | All 19 input contracts record source paths/hashes, base-output hashes, 91 genes, 25 factors and the same SCT-v2-log1p description. This does not establish how the upstream Y was created. |
| H-P base to observations | Local `P/production/build_section_mesh.py:111-112,251-258` loads every base array and exports `**base`, adding geometry arrays. No response transformation or cell/gene selection occurs at that boundary. Remote mesh certificates record output hashes. Actual historical arrays were not compared. |
| H-P observations to GPINIT | All 19 GPINIT source paths/hashes match the intended observation paths and mesh certificates; cells, genes and factors agree. |
| H-P base to H-C preparation | Every H-C input certificate's source hash matches the corresponding H-P base-output hash. All 19 copied source contracts are missing at the queried H-C paths. |
| H-C retained observations to GPINIT | All 19 source paths/hashes and dimensions match their input certificates. Bundle metadata supplies all 19 GPINIT output hashes. |
| Observations and GPINIT to actual sampler invocation | Not established. The inspected cloud wrapper delegates to `cloud_run.py`, which was not inspected. No executed per-run command/input-manifest chain was recovered. |

The local transfer preserves Y, ordered gene/cell identities, cell IDs,
source-row indices and centering means. This is static implementation evidence;
identity arrays in the historical NPZ files were not opened. The common
91-gene order is recorded in the preparation summary, and all production
contracts declare stable contiguous MIC/AST/OGC blocks.

### All-section findings

Every row has matching recorded full and retained observation-to-GPINIT hashes,
matching base-to-retained-source hashes, matching GPINIT source paths, and
matching dimensions. All 38 GPINIT certificates report PASS, 91 genes, three
cell types and nfit=250. Full-cell inputs use 25 factors; retained inputs use 20.

Residuals below are the historical certificates'
`maximum_input_recentering_mean`, not newly computed array measurements.

| Section | Full cells | Retained cells | Full residual | Retained residual | Recorded links |
| --- | ---: | ---: | ---: | ---: | --- |
| S00__Trem2_5xFAD4 | 9451 | 4726 | 2.886404074135313e-14 | 8.560459357068575e-15 | Match |
| S01__5xFAD4 | 11938 | 5970 | 4.48871636658681e-14 | 7.585023977899931e-15 | Match |
| S02__Trem2_4 | 8949 | 4475 | 3.893433777993828e-14 | 3.137047171313676e-15 | Match |
| S03__Trem2_5xFAD3 | 10557 | 5279 | 5.151870306675977e-14 | 8.689845765042694e-15 | Match |
| S04__WT3 | 8308 | 4154 | 4.920460174572406e-14 | 3.9392454851527474e-15 | Match |
| S05__Trem2_3 | 10128 | 5064 | 7.791113865378894e-14 | 9.092135243898763e-15 | Match |
| S06__5xFAD3 | 11387 | 5694 | 7.79803603973186e-14 | 8.827866172361425e-15 | Match |
| S07__Trem2_5xFAD5 | 8054 | 4028 | 5.572289651036838e-14 | 3.634111576366535e-15 | Match |
| S08__5xFAD5 | 8609 | 4305 | 3.1753670212277874e-14 | 4.4414087816999865e-15 | Match |
| S09__Trem2_5 | 9015 | 4508 | 5.491833974801158e-14 | 3.3888360820726433e-15 | Match |
| S10__WT5 | 9422 | 4712 | 5.0171521704530475e-14 | 7.106736068435531e-15 | Match |
| S11__Trem2_5xFAD1 | 10913 | 5457 | 5.855806218571095e-14 | 7.962852392773568e-15 | Match |
| S12__Trem2_1 | 11650 | 5826 | 4.8211385433223975e-14 | 1.0826147601551898e-14 | Match |
| S12__Trem2_5xFAD2 | 13485 | 6743 | 5.974261814416795e-14 | 9.367729408581835e-15 | Match |
| S13__Trem2_2 | 5055 | 2529 | 1.937445538513412e-14 | 2.5951193729005114e-15 | Match |
| S14__WT1 | 9424 | 4713 | 5.228295284244153e-14 | 4.983251839508237e-15 | Match |
| S15__5xFAD1 | 10875 | 5438 | 6.286583596153217e-14 | 4.915269987347144e-15 | Match |
| S16__WT2 | 8200 | 4101 | 4.4943191370585815e-14 | 3.569363569835639e-15 | Match |
| S17__5xFAD2 | 11680 | 5841 | 4.299639854178387e-14 | 5.016888060915495e-15 | Match |

The section registries agree, including both distinct S12 identifiers. Individual
production contracts agree with their summary entries. Source counts agree by
cell type, and each retained type count equals ceil(source count / 2).
The largest recorded residual is 7.79803603973186e-14 for full-cell inputs and
1.0826147601551898e-14 for retained-cell inputs.

These small residuals support the inference that GPINIT's additional centering
removed floating-point residue. They do not demonstrate bitwise equality,
scientific validity of the chosen response, or later sampler consumption.
The inspected branches are full-cell/25-factor and retained-cell/20-factor;
this is not an audit of every historical campaign or 75%-cell variant.

### Configurations and remaining limitations

| Evidence type | Finding |
| --- | --- |
| Code defaults (B2) | GPINIT defaults to 5 factors, nfit=500, seed=0. |
| Configured production wrapper (B2) | Factors are read from the base artifact; nfit=250 and seed=2026102400 + task ID are supplied. |
| Configured consolidation wrapper (B3) | `CS/prepare_cpu.sh:13-16` supplies 20 factors, nfit=250 and seed=2026102600 + index. |
| Historical GPINIT records | Certificates record factors and nfit as above. Seeds are not recorded in these certificates. |
| Production launch contract | Records four chains/section, 25 factors and pilot PASS claims; not each executed command/artifact pair. |
| Consolidation package result | Records READY_FOR_CLOUD_GPU_PREFLIGHT, 19 sections and GPU_smoke_run=false. No completed cloud sampler run is established. |

The missing copied contracts do not invalidate the matching recorded base hashes,
but they remain missing evidence. Export certificates retain
EXPORTED_AWAITING_SAMPLER_VALIDATION while later GPINIT certificates report PASS;
these concern different stages and are not alone a contradiction. The inherited
driver-centering documentation discrepancy from B2 remains.

No live NPZ content/hash, source implementation on HPC, or current artifact
identity was independently verified. The captured metadata establish historical
records and internal consistency, not fresh verification of large artifact bytes.

### Remaining upstream gap and proposed B4

SCTransform invocation, v2 arguments, R/Seurat/sctransform versions, corrected-count
assay/slot/layer, log1p placement, raw-input provenance, and actual execution of
the upstream exporter remain unresolved. The repeated SCT-v2-log1p description
is a historical claim, not certification.

Proposed B4 is bounded to one nonrecursive filename listing of H-U and H-U/audit,
small README/index/manifest/provenance records, and the referenced
`H-U/audit/SECTIONS.csv`. Those records should identify the exact SCTransform
invocation and exporter writing each `input.npz["Y"]`, followed by directly
referenced version/execution records across all 19 sections. Exact script names
have not yet been discovered. NPZ/RDS/Seurat objects remain unopened and
unhashed. No B4 inspection is performed in this checkpoint.

The separate sampler-consumption gap requires the response-path portions of
`cloud_run.py` and actual run-command/input-manifest records. Their locations
must be established before expanding inspection. No implementation has been
selected or imported; neither SCTransform creation nor actual sampler invocation
has been certified.

## B4 accepted incomplete increment

The user accepted B4 as an important but incomplete provenance checkpoint.
`H-U/review.py` was identified as the exporter; it does not implement SCTransform
itself. The [B4 ledger](SCTRANSFORM_EVIDENCE.md#b4-capture-preservation-and-validation)
records acquisition, source hashes and evidence limits. The
[B4 section table](SCTRANSFORM_B4_SECTIONS.csv) records all 19 source branches and
artifact links. Metadata captures are preserved in Git; the two captures containing
legacy source text are preserved outside Git at the user's specified stable paths.

### Raw source and export graph

W denotes `E:\johnston_brain`; N denotes
`E:\johnston_brain\artifacts\GENE_REVIEW_20261004`. These are historical Windows
references, not newly accessed locations. Source references below are to the
measured `H-U/review.py`, lines 1-138 only.

```text
W/Johnston_MERFISH_Data.h5ad
  layers/RNA + var/_index + observation labels/identities + obsm/spatial
  -> section mask: sample code AND gen_fine section label
  -> all selected section cells and original genes
       |
       +-> nine reused historical SCT CSVs
       |     -> branch-specific cell/coordinate/count identity checks
       |
       +-> ten recorded new sections
             -> counts.mtx + genes.txt + cells.txt
             -> OUT/sct_section.R [missing from inspected package]
             -> sct_data.csv.gz [may already exist; R invocation then skipped]
       |
       -> read SCT CSV; check exact expected cell-column order and gene names
       -> reindex into original gene order; compute per-gene availability
       -> select Mic/AST/OGC cells in original source-row order
       -> input.npz Y: genes x glial cells, no added log/centering/scaling
       -> B1/B2 panel selection and centering -> B3 observations/GPINIT links
```

| Transition | Implemented behavior and limits |
| --- | --- |
| Raw source | `review.py:70-80` reads H5AD `layers/RNA` and asserts proximity to integers within 1e-8. Earlier provenance/filtering of this H5AD is not recovered; no H5AD was opened during recovery. |
| Section selection | `:71-79` uses sample codes and `gen_fine`, checks registry cell counts, and preserves source-row order. Both S12 sections are separately selected by their fine labels. |
| Legacy branch | `:82-94` uses six sct_work exports and checks global row/coordinate identities, or raw-count equality. `:95-109` uses three region_story exports and checks ordered coordinates (allowing a global x/y swap), labels and column identifiers. These are identity checks, not proof of the normalization recipe. |
| New R inputs | `:110-115` rounds counts to integers, casts int32 and transposes to genes x cells before export. Glial selection occurs later. The missing R implementation prevents verification of its internal filtering or actual fitting population. |
| R dispatch | `:22,117-118` configures `C:/Program Files/R/R-4.5.3/bin/Rscript.exe`, passes `OUT/sct_section.R` and the section directory, captures `sct.log`, and checks subprocess success. The configured executable path is not a measured runtime version. |
| Expression alignment | `:121-125` reads the CSV, requires its column names in expected order and unique genes from the original list, reindexes rows and converts values to float. Available genes must have nonnegative expression. |
| Glial export | `:126-130` retains Mic, AST and OGC in original source order. Y is exported without another log, centering or variance scaling. The later B1/B2 preparation performs stable type grouping and centering. |
| Readiness | `:131-135` records dimensions, SCT source/hash, identity-check description and an already-log1p claim. A preexisting READY record skips the whole section (`:77`); a preexisting new-branch CSV skips R (`:112-119`). |

| Output field | Meaning at export (`review.py:124-130`) |
| --- | --- |
| Y | Aligned SCT CSV values, genes x glial cells. Upstream corrected-count/log1p construction remains unverified. |
| raw | Glial subset of layers/RNA, transposed and cast to int32. |
| genes | Original H5AD var/_index order. |
| types | Original cluster_coarse labels for selected cells: Mic, AST, OGC. |
| available | Finite expression across all selected section cells, before glial subsetting; unavailable rows remain represented after reindexing. |
| source_rows / native_cell_names | Global H5AD row indices / original observation names for retained cells. |
| cell_names / xy / regions | Branch-specific SCT column names / native coordinates / region labels, aligned to retained cells. |

### Two normalization lineages and three gene sets

The 19 READY records classify **ten new SCT exports and nine reused historical
exports**. This describes recorded provenance, not ten independently observed R
executions. The reused branches are:

- sct_work: S04, S06, S14, S15, S16 and S17;
- region_story: S01, S08 and S12__Trem2_5xFAD2.

Every exact section ID and source path is in the B4 CSV. For all 19 sections,
readiness all-cell counts equal the registry, glial counts equal the sum of the
three type counts and B3's full-cell counts, and 300 genes are recorded available.
Fresh readiness hashes match the bundle; all 19 recorded bundle input hashes
match B3's recorded upstream source hashes. These are verified metadata
comparisons, not fresh matrix hash/content verification or sampler execution.

| Gene count | Stage and evidence |
| --- | --- |
| 300 available | Every READY record reports 300; audit/GENE_EVIDENCE_INDEX.csv has 300 records. The exporter retains the original gene list and computes availability. This is not a newly inspected matrix shape. |
| 72 review candidates | README.txt:6-9 describes the union of prior S15/S6 panels and paper-motivated genes. review.py:39-65 builds candidates separately; preparation does not use that list to restrict Y. The saved CANDIDATES.csv was not read in B4. |
| 91 modeled genes | B1/B2 panel selection and B3 contracts describe the later common modeling panel. This does not imply that the 72-candidate review established that panel's final selection rationale. |

### Certification gap and B5 boundary

README.txt:13-20 claims per-section SCT v2, no Pearson-residual input, no second
log1p and no SD standardization. It explicitly states that cross-section
correction depths were not harmonized and legacy models/reference depths were
not known. READY records repeat the already-log1p and non-harmonization claims.

The exporter establishes no extra log or scaling at its own boundary. It does
not establish the original assay/slot/layer, corrected-count definition, number
of upstream log applications, SCTransform arguments, package versions, seeds or
execution provenance. The two normalization branches are not yet shown comparable.
This is a provenance gap, not a demonstrated numerical preprocessing failure.
The earlier centering findings remain intact.

The README's stated purpose was to authenticate/reuse existing exports and fill
missing section coverage. No inspected normalization comparison or historical
user approval establishes superiority. Subsequent artifact adoption is supported
by the 19 recorded hash links to B3; actual sampler invocation remains unresolved.

B5 is proposed, not performed. First locate the missing sct_section.R. Its
package-relative reference is H-U/sct_section.R; the inferred historical Windows
location is N/sct_section.R, whose existence is unverified. Then recover small
version/execution records for the ten new sections and the creator implementations
for the nine reused exports. External paths and narrow proposed discovery roots
are recorded in the ledger. No external location was followed during B4 or this
checkpoint. No implementation is selected or imported.
