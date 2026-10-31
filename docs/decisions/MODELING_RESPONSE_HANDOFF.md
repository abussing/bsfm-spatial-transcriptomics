# Canonical modeling-response handoff

Status: **approved design; single-section implementation and bounded S00 gate
accepted; multi-section orchestration and remaining-section execution pending**.
Authority: explicit user approval following the bounded metadata design gate.
Baseline: `570bd3e41f77518e136cb3a8f17a9e6e62955f0f`.

Subsequent implementation gate: the user authorized a single-section runner and
independent validator from checkpoint `51441c885ecf5f4ac19d10a8b399d7d1ade46e1f`.
The [S00 review report](../preprocessing/audits/20261031_response_S00/summary.md)
records regenerated S00 review evidence, exact accepted-response equivalence and
six-file isolation after removing the external attempt-log dependency.
The single-section implementation, independent validation, S00 equivalence and
six-file portability are accepted. Both generated bundles remain review evidence
from uncommitted code, not future all-section production artifacts. The original
frozen specification below is unchanged. This does not authorize the remaining 18 sections.

This decision extends the [SCTransform design](SCTRANSFORM_DESIGN.md) and the
[accepted bounded validation](../preprocessing/SCTRANSFORM_VALIDATION.md).
It authorizes registries, schemas and documentation, not a production runner,
additional normalization, centering, meshes, GP initialization or HPC execution.
No historical implementation is selected or imported.

## Canonical panel and evidence

The authoritative ordered panel is now
[modeling-panel.json](../../config/preprocessing/modeling-panel.json), validated
structurally by its [schema](../../schemas/preprocessing/modeling-panel.schema.json).
It contains all 91 names, zero-based raw 300-gene positions, evidence references
and the approved ordered SHA-256:

```text
48e934a62161d7fb69e3abb3e636a979660b6e1b62cbacdcec929c2584d8bfa8
```

Hash each original UTF-8 identifier prefixed by its uint64 little-endian byte
length, concatenated in order. No case, whitespace or alias normalization occurs.
All names occur exactly once in the accepted raw panel, and their relative raw
order matches this panel. Exact registry content and hash must also be checked;
JSON Schema validation alone does not authenticate the panel.

This is a new authoritative project decision supported by the shared historical
preparation contract, not a claim of independent historical matrix verification.
The shared `gene_order` is at lines 8-100 of the committed
[B3 capture](../recovery/evidence/sctransform_b3/s00_and_preparation_summary.txt).
All 19 individual contracts match their embedded entries and record `genes=91`,
but none records its own ordered list. No expression matrices were opened in
this gate. Panel selection independence from future holdouts is unestablished.

## Identity and coordinates

| Identity | Authoritative source |
| --- | --- |
| Section | Exact decoded `obs/sample` plus `obs/gen_fine`, using the frozen [section registry](../../src/bsfm/preprocessing/sections.json) |
| Animal | Original decoded `obs/gen` |
| Genotype | Original decoded `obs/gen_coarse` |
| Cell | Original `obs/_index` identifier plus zero-based global raw source row, namespaced by the raw-source fingerprint |
| Gene | Original `var/_index` identifier and zero-based raw gene position |
| Type | Original `obs/cluster_coarse`; `Mic -> MIC=0`, `AST -> AST=1`, `OGC -> OGC=2` |

There are 19 sections and 15 recorded animal labels. Never infer animal identity
from the section suffix. Raw `gen` and `gen_coarse` agree with all historical
mouse/genotype contract entries. Four section labels differ from animal labels:

| Section | Recorded animal |
| --- | --- |
| S12__Trem2_5xFAD2 | Trem2_5xFAD1 |
| S13__Trem2_2 | Trem2_1 |
| S16__WT2 | WT1 |
| S17__5xFAD2 | 5xFAD1 |

This mapping is adopted from the source and corroborated by B3; it is not
independent authentication against an animal/sample sheet. The two S12 sections
share `sample` and are disambiguated by `gen_fine`.

Preserve decoded `sample`, `gen_fine`, `gen`, `gen_coarse`, `cluster_coarse`,
`coarse_batch`, `region_labels` and `region_labels_coarse`. Keep original type
labels and the textual/numeric mapping alongside codes. Nonglial cells remain
in the all-cell normalization population and retain their raw labels; they
are not assigned a modeled MIC/AST/OGC code.

Coordinates are copied **unchanged** from `obsm/spatial`, with:

```json
{
  "axis_order": ["center_y", "center_x"],
  "units": "source_native",
  "raw_unit_declaration_status": "not_found"
}
```

Every source coordinate row exactly equals `[obs/center_y, obs/center_x]`.
Do not swap, scale, translate, rotate or reflect the preserved coordinates.
Historical `coordinate_scale_microns` is retained separately as the claim
`microns`, with its B3 evidence reference. Canonical coordinates are not verified
microns. Physical-unit authentication belongs to the later mesh-design gate.
No anatomical axis directions are inferred from the column names.

## Section bundle v1

The [machine-readable bundle specification](../../config/preprocessing/response-bundle.json)
defines the dataset paths, dimensions, types, ordering and completion rules.
Its [schema](../../schemas/preprocessing/response-bundle.schema.json) freezes the
approved specification. The [final-manifest schema](../../schemas/preprocessing/response-manifest.schema.json)
describes completed full-data bundles only. These are contracts, not an
implemented HDF5 writer or validator.

Each external section bundle contains `response.h5`, `fit.rds`, `execution.json`,
`session.txt`, `validation.json` and final `manifest.json`. All large artifacts
and cell-level identifiers remain outside Git. Retain any additional fit logs
or assay objects externally and identify their locations, sizes and hashes in
the execution record; they do not replace the required artifacts.

Let N be all eligible section cells and M all selected MIC/AST/OGC cells.

| HDF5 object | Shape | Meaning |
| --- | --- | --- |
| `axes/genes300`, `axes/cells_all` | 300 and N | Explicit IDs and raw positions/source rows |
| `all/corrected_counts` | 300 x N | Finite, nonnegative, integer-valued float64 corrected counts |
| `all/log1p_response` | 300 x N | Exactly one natural `log1p` of corrected counts |
| `axes/genes91`, `axes/cells_model` | 91 and M | Panel IDs, selected IDs, raw indices and mappings into all-cell/all-gene axes |
| `model/uncentered_response` | 91 x M | Exact identity-based subset of the all-cell response |
| `model/centered_response` | 91 x M | Final immutable response for both GPINIT and BSFM |
| `centering/means` | 91 x 3 | One arithmetic mean per section/type/gene |
| `centering/group_sizes` | 3 | Actual modeled-cell group sizes |
| `coordinates/all_source`, `coordinates/model_source` | N x 2 and M x 2 | Unchanged aligned source coordinates |
| `metadata/all/*`, `metadata/model_type_code` | N and M | Preserved raw metadata and selected canonical type codes |

All-cell columns follow increasing raw source row. The 300-gene axis preserves
raw order; the 91-gene axis follows the approved registry. Modeling columns form
stable MIC, AST, OGC blocks, with increasing source row within each block.
There is no thinning. Mean columns follow the same explicit type axis.
Every matrix axis references an explicit identity dataset and ordered hash;
consumers must verify the IDs and mappings rather than assume array position.

For actual modeled cells I[s,t] in section s and type t:

```text
L[g,i]    = log1p(C[g,i])
mu[s,t,g] = sum(L[g,i] for i in I[s,t]) / len(I[s,t])
Y[g,i]    = L[g,i] - mu[s,type(i),g]
```

Compute means once after selection, preserve L and mu, and apply no variance
scaling or second logarithm. Any future approved cell subset requires a separate
response identity and means. Downstream GPINIT and BSFM consume the same final Y
without further response transformation.

Retain the full fitted SCT state, realized fitting-cell identities, gene
availability and effective arguments. No missing required output gene may be
silently dropped or filled. Preserve execution commands, code commit, frozen
configuration, raw and registry identities, environment source/renv locks,
package/session/platform information, seeds/RNG, threads, warnings and exit
status. The unresolved namespace stack-imbalance diagnostic remains documented
in the bounded validation evidence; occurrence during normalization stays fatal.

Numeric payload hashes use declared little-endian dtype and logical C-order
values; shapes and axis hashes are recorded separately. String payload hashes
use the length-prefixed UTF-8 encoding above. File SHA-256 and byte sizes identify
serialized artifacts independently of logical dataset hashes. The manifest
does not include its own hash; the parent run ledger records that after closure.

JSON Schemas check structure and fixed values, not HDF5 contents or execution.
The future validator must independently check shape relationships, unique axes,
source joins, fitting cells, gene availability, method, layer equality, exact
selection/coordinate preservation, centering and reconstruction, and all hashes.
Floating-point tolerances must be explicit in the reviewed runner configuration
before execution, with actual residuals recorded. This decision performs none
of those response operations and claims no completed canonical section bundle.

## Full-data versus primary holdout artifacts

Version 1 final manifests require:

```json
{
  "preprocessing_regime": "full_data",
  "correction_depth": 124,
  "primary_holdout_scoring_eligible": false,
  "fold_id": null,
  "panel_selection_independent_of_holdouts": "unestablished"
}
```

Full-data bundles are unsuitable for primary holdout scoring. A future separately
approved training-only schema must identify fitting cells, correction-depth
estimation populations, centering populations, folds and the frozen held-out
scoring transformation independently. It must not silently inherit full-data
depth or means. Fixed-panel evaluation does not certify panel-selection
independence from held-out expression.

## Completion and recovery from interruption

1. Write to a unique temporary attempt directory on the destination filesystem.
2. Close and flush artifacts, reopen them, and validate all required identities,
   dimensions, numerical invariants and hashes.
3. Write the final manifest only after validation passes.
4. Promote by same-filesystem directory rename to a previously absent immutable
   final destination. Never overwrite a completed section.
5. Accept only a final bundle with a complete manifest and matching validation
   and hashes. Directory existence or process exit never establishes success.
6. Reuse an interrupted stage only after closed-file validation and exact
   input/code/config/environment/dependency identity agreement. Otherwise start
   a new attempt. Partial files remain incomplete.
7. Mark the overall run complete only when all 19 final section manifests pass
   under one frozen run specification. Recheck hashes after interruptions;
   promotion is not a substitute for integrity checks.

## Supporting metadata audit and remaining work

The [aggregate metadata audit](../preprocessing/audits/20261031_response_metadata/audit.json)
and [section table](../preprocessing/audits/20261031_response_metadata/sections.csv)
record the read-only checks. All 432,794 rows belong to exactly one section;
187,100 glial IDs are unique and have finite coordinates. Every section/type
count matches B3 and the accepted raw audit. All 19 historical coordinate
origins/scales agree with raw-order glial coordinates. The accepted whole-file
fingerprint was reused; cell/gene order hashes were recomputed, and source size
and modification time were stable. Expression arrays were not read.

The single-section runner, independent validation and numeric tolerances have
subsequently been accepted as recorded above. Remaining gates include
multi-section orchestration, physical coordinate units for mesh design, and
training-only holdout design. No additional normalization, response centering,
mesh/GP work or job submission is authorized by this documentation checkpoint.
