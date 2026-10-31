# M3 coordinate/topology evidence preservation

The measured M3 audit is complete. This receipt preserves the already collected
evidence; no coordinate audit, mesh generation or numerical study was rerun.
The governing approval is the [canonical design](../../../decisions/ADAPTIVE_MESH_DESIGN.md).
The original proposal documents are evidence of the discussion, not executable
configuration or the current scientific authority.

## Evidence locations and authentication

Original temporary directory (not a durable dependency):
`C:\Users\Data Viz\AppData\Local\Temp\bsfm_mesh_m3_35a2221`.

Eight metadata/report/table captures, **1,199,552 bytes total**, are preserved
byte-for-byte under
[docs/recovery/evidence/adaptive_mesh_m3](../../../recovery/evidence/adaptive_mesh_m3).
They are audit.json, M3_REPORT.md, protocol.json, resource_estimates.json,
sections.csv, section_comparison.csv, study_proposal.json and artifact_hashes.json.
The repository evidence attributes preserve their original bytes.
The local evidence attribute recognizes original CRLF JSON/report endings for
whitespace checks; it does not normalize or alter their authenticated bytes.

The coordinate contact sheet and three temporary diagnostic scripts remain
outside Git, **3,095,390 bytes total**, at the machine-local stable path:

`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\adaptive_mesh_m3`

Files: geometry_review.png, reader.py, audit_geometry.py, check_and_review.py.
These scripts are diagnostic acquisition evidence, not selected canonical mesh
code or an implemented Phase-0 harness. The external location is not an
off-computer backup. Source coordinate arrays were never saved as audit outputs.

The [evidence inventory](evidence-inventory.csv) gives exact original/preserved
paths, byte counts, SHA-256 values and classifications for all 12 files. The
original artifact_hashes.json authenticates its eleven siblings; it is itself
authenticated by this inventory. All copies were checked against original bytes
and the recorded hashes before and after preservation. Existing differing files
were refused, not overwritten. The pre-compaction audit hash inside audit.json
identifies an earlier representation that was not separately retained; the
preserved compact histograms contain all component-size multiplicities.

The audit SHA-256 is
`a85812eb8035bd324623171cf246bea11838a2a8e1df8e90c5f8754f977e78c8`.
The original report SHA-256 is
`7df6a21aad35a98fd018c8b33c4fc6ae28c0e0f08f630e7981df08d20c3ae6a3`.

## Acquired evidence and limitations

M3 baseline: `35a22212528d24daba218e48da54a9f8ee8f0c76`.
Canonical input root (machine-local):
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2`.
The [committed production receipt](../../../preprocessing/audits/20261031_production_v2/README.md)
records generating commit `6eb672bebbaf5cde6c9d50391aac275a210832a6` and final
run-manifest SHA-256
`03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f`.

M3 authenticated the run manifest, all 19 section manifests, and allowlisted
coordinate/identity datasets with semantic hashes. It checked canonical registry
selection metadata, unique IDs/source rows, finite coordinates, and exact joins
between all-cell and modeling-cell rows. It did not rehash whole response.h5 files
because doing so would read expression payload bytes. No expression dataset,
raw-H5AD array, fitted model or mesh was read. No HPC or further legacy search
occurred. This checkpoint validates preserved evidence, not production arrays.

The temporary reader used existing Anaconda Python/h5py; coordinate arrays were
transferred in memory to existing Python 3.12.0, NumPy 2.4.1 and SciPy 1.18.1.
The Anaconda SciPy spatial import failed before input reads; no installation or
environment modification was made. The scripts and recorded versions preserve
this acquisition method. They should not be run as canonical production code.

Evidence classes:

| Class | Scope |
| --- | --- |
| Measured canonical geometry | 19 registered sections, 38 populations, 432,794 all cells and 187,100 modeled glial cells; source_native coordinates. |
| Authenticated observations | Dataset hashes and identities; 228 radius-component histograms; 38 independent direct-radius comparisons; 12 finer-grid hole checks. |
| Geometric interpretation | Empty regions and components depend on explicitly recorded scales; not authenticated anatomical boundaries. |
| Mathematical derivation | Common-scale/range transformations and central prior interval. |
| Original proposal | study_proposal.json and report design/resource passages; superseded where amended by the canonical decision. |
| Planning estimates | resource_estimates.json, not measured mesh performance. |
| Explicit user decision | Broad M3 design and staged protocol, recorded in the canonical decision. |

No exact duplicate locations were observed. Near-coincident cells and gaps are
not evidence of invalid cells. The geometry contact sheet has raw source axes
translated/scaled for review; it establishes neither physical units nor anatomy.

## Supersession and table conventions

Do not silently promote the original report's amplitude coupling, two-grading
108-candidate proposal, secondary tolerances or tail stop policy. The current
decision uses unit amplitude, one experimental grading rule and staged counts:
6 pilot + 48 additional representative + at most 20 confirmation geometries.
The original 108 count explicitly multiplied two grading levels; retaining it
after reducing that factor to one would be incorrect. Pilot measurements are
reused, not counted twice. Some original text contains encoding artifacts such
as `Mat?rn`; preservation retains those bytes without correcting the evidence.

CSV files have headers. sections.csv has 38 rows (section then population);
section_comparison.csv has 19 rows in registry order. Semicolon lists follow the
predeclared scale order in protocol.json. audit.json contains all component-size
histograms (size to multiplicity), nine NN quantiles, coordinate spans, aggregate
hole geometry, identities and independent check results. It contains no cell-ID
lists or expression values. JSON files parse fully, without acquisition head
limits or truncation. Their existing schemas are preserved, not rewritten.

The new [study specification](../../../../config/mesh/study-design.json) is a
version-1 design record, not a production artifact schema or run authorization.
Its [schema](../../../../schemas/mesh/study-design.schema.json) and cross-table
checks constrain factors, section partition, ranges and counts. The
[geometry table](../../study-geometries.csv) enumerates all 54 representative
geometries with their first phase; the [range table](../../study-ranges.csv)
separates 21 central points from two tail diagnostics. The
[confirmation table](../../study-confirmation.csv) lists the ten remaining
sections and conditional maximum slots, not invented finalist identities.

## Checkpoint checks

Preservation uses byte reads/writes, SHA-256 and standard JSON/CSV parsing. No
scientific source executes. Checks cover inventory copies, original hash
manifest, complete metadata parsing, canonical section/order/count relationships,
228 histogram totals, 38 direct-graph results, 12 refined-hole records, common
scale, source-manifest identity links, schema, all enumerated factors and
evaluation totals, local documentation links, credential patterns and Git diff.
Staged review excludes scripts, plots, arrays, fitted objects and environments.
No mesh accuracy, performance or production acceptance result exists yet.

The [checkpoint check record](checks.json) reports these preservation, schema,
table, hash, link and credential checks separately from scientific validation.
