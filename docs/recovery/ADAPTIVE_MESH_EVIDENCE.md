# Adaptive-mesh evidence ledger through M2

Current decision: the subsequent [canonical M3 design](../decisions/ADAPTIVE_MESH_DESIGN.md)
freezes broad scientific choices and a staged study. The M1/M2 status and open
questions below describe that historical checkpoint; no implementation was selected.

Status: bounded historical recovery complete; no implementation or numerical
design selected. Baseline `1c9f36331fd55d3ddd1953199499fe084f30293f`.
The user authorized M1/M2 read-only recovery and then this documentation commit.
This is not approval of a mesh recipe or another scientific computation.
See the [recovery report](ADAPTIVE_MESH.md).

## Evidence and table conventions

This follows [RECOVERY_PROCESS.md](../RECOVERY_PROCESS.md) and the existing
[SCTransform evidence convention](SCTRANSFORM_EVIDENCE.md). Evidence classes are
explicit in [ADAPTIVE_MESH_EVIDENCE.csv](ADAPTIVE_MESH_EVIDENCE.csv): verified
source behavior, authenticated historical measurement, documented historical
claim, mathematical inference, unresolved scientific choice, and explicit user
decision. A certificate PASS is not a claim of universal scientific validity.
Conversation approvals are identified by topic; no invented message ID or
historical approval transcript is supplied.

| Table | Purpose |
| --- | --- |
| [ADAPTIVE_MESH_SOURCES.csv](ADAPTIVE_MESH_SOURCES.csv) | Original stable external paths, full-file sizes/hashes and inspected scopes; equal hashes identify duplicate bytes, not independent evidence. |
| [ADAPTIVE_MESH_METADATA_CAPTURES.csv](ADAPTIVE_MESH_METADATA_CAPTURES.csv) | Exact original and repository paths, bytes and SHA-256 of 30 verbatim metadata/documentation captures. |
| [ADAPTIVE_MESH_M2_REPORTS.csv](ADAPTIVE_MESH_M2_REPORTS.csv) | All 19 archive member paths, sizes/hashes, preserved paths, pass/full-rank status and per-section numerical maxima. |
| [ADAPTIVE_MESH_M2_RANGES.csv](ADAPTIVE_MESH_M2_RANGES.csv) | Six range rows with continuum/variance extrema and discrete error maxima across 19 reports. |
| [ADAPTIVE_MESH_M2_NUMERICAL_SUMMARY.json](ADAPTIVE_MESH_M2_NUMERICAL_SUMMARY.json) | Derived archive identity, section order, 114 comparisons, global maxima and limitations. |
| [ADAPTIVE_MESH_EVIDENCE.csv](ADAPTIVE_MESH_EVIDENCE.csv) | Claim-specific evidence strength and limitations. |
| [ADAPTIVE_MESH_DECISIONS.csv](ADAPTIVE_MESH_DECISIONS.csv) | Unresolved design-gate questions; none is silently frozen. |

CSV files are UTF-8/LF with a header and standard CSV quoting. Hashes are
lowercase SHA-256 of whole file/member bytes, not scientific payload hashes.
`preserved_path` resolves relative to docs/recovery. Section rows follow F's
SECTIONS.json order, matching the canonical registry IDs. `*_max` fields are
maxima across that section's six reports, except range-table maxima across
sections. Continuum errors are relative Frobenius discrepancies; projected
variances are the recorded diagonal extrema. True/False CSV values are explicit
booleans, not evidence classifications.

The derived summary's schema_version=1 identifies this audit record, not a mesh
artifact contract. Fields and types are checked against its documented table
relationships: 19 unique sections, six fixed ranges, 114 comparisons, finite
metrics, PASS/full-rank records, exact extrema and linked hashes. Historical JSON
is retained under its original structure rather than rewritten into a new
completion schema. No production mesh schema is introduced.

## Exact path aliases (machine-local unless noted)

| Alias | Path |
| --- | --- |
| E | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CURRENT_20261014\bayesian_spatial_factor_model` |
| L | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_LI_KERNEL_GATE_20261014` |
| P | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_19_SECTION_PRODUCTION_20261024` |
| C | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030` |
| CS | C plus `source_snapshot` |
| A | `D:\johnston_brain\artifacts\MESH_LINEAGE_AUDIT_20261026` |
| F | `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1` |
| W | `D:\johnston_brain\run_bundles\warp_range_study_v1` |
| R | `C:\Users\Data Viz\Desktop\Anderson_Hail\bsfm_mesh_review_20261030` |
| Z | `C:\Users\Data Viz\Downloads\BAYESIAN_SPATIAL_FACTOR_MCMC_20261014.zip` |
| RAW | `D:\johnston_brain\Johnston_MERFISH_Data.h5ad` |

HPC paths embedded in historical records are provenance only. M1/M2 and this
checkpoint made no HPC connection. External paths are not portable retrieval
identifiers or an off-computer backup.

## Acquisition boundaries and inspected evidence

M1 confirmed the clean checkpoint and canonical SCT receipt; read AGENTS,
CAPABILITIES, README and coordinate/response documents. It used shallow listings
of the named desktop roots and relevant D: artifact/run-bundle roots, plus
specific manifests/indexes. Z was listed only (72 members, 274336 bytes); its
contents were not extracted. E/L/P/C reflect overlapping lineage.

Relevant metadata included E's FILE_INDEX.json, MANIFEST.json, START_HERE.txt and
provenance schema/study manifest; P's production manifest; C's README,
CLEANUP_FINDINGS, RUN_SPEC_TO_DECIDE and source-snapshot SOURCE/BUNDLE/INPUTS
manifests, README_L4 and PACKAGE_RESULT; A/AUDIT.txt; F's WORK_LOG, preview summary,
input/source certificates; W's STUDY_SPEC_DRAFT and geometry validation; and R's
counts. The committed B3 captures provide existing all-19 GPINIT linkage.
These were inspected as metadata, not executed authority. Decisive verbatim
captures and exact original paths are enumerated in the metadata table.

Source reads were reference-led. The source table gives exact scopes and full
file identities; whole-file hashing is not a claim that unrelated functions were
inspected. M2 used AST/line extraction without importing modules. Necessary
direct-W dependencies were read only to trace geometry, amplitudes and priors.
Five named consumer/dependency files are byte-identical between E and F; the
drivers differ overall but the inspected prior/loading blocks match. M1's A/F
build_preview.R copies and F/CS preparation/validation copies also match.

The B4 captured review.py excerpt remains at the stable external path recorded
in the source table, SHA-256
`3a4140ada8241aecad31b4702bd4c0754a38caff471f8c19114535a96ab06da3`.
No new legacy source captures were created inside Git. Other inspected sources
remain at their original external paths, with size/hash references; this is not
a promise of permanent retention or immutability of those external files.

M2 exact negative checks combined each of these three parent directories:
`D:\johnston_brain`, `D:\johnston_brain\artifacts`,
`D:\johnston_brain\run_bundles`, with each of:

- `real_splusu_mesh_preview_20260908_v1/build_real_mesh_preview.R`
- `real_mesh_graded_buffer_v3/build_mesh_ladder.R`
- `mesh_sensitivity_work/CORRECTED_MESHES_V3.md`

All nine checks were negative. Named-file searches in A/AUDIT, existing C
inventory/manifests, E's function index and D's known handoffs found later
references, not the original source. No recursive drive-wide search occurred.

S12 INPUT_CONTRACT records were read; cells.csv was only located/stat'ed. No
generation attestation was recovered. R's nonrecursive inventory has images,
PDF and counts but no generation record. M1 viewed one S12 comparison image;
no images were copied into Git. Matching labels/counts are not byte-authenticated
plot provenance. The FULL_cells contact sheet's exact generation remains open.

M2 read RAW HDF5 schemas/attributes and small spatial scalar metadata via h5py
read-only mode, not expression/coordinate/image arrays. RAW was not rehashed or
fully scanned. It inspected bounded passages of the directly associated
`D:\johnston_brain\johnston_paper.txt` and the known HANDOFF. The canonical
raw-unit conclusion remains not_found. The raw scalar findings are a recovery
observation recorded here, not a retained verbatim acquisition capture.

## Archive authentication and verbatim reports

Exact archive:
`D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1_READY.tar.gz`

- Bytes: 98111074.
- SHA-256: `4458f784c8e760893c5fcd620f8ec74f40d9f504a0fa7d5fcbda9f29fe600f07`.
- Members: 442; requested numerical reports: 19, all present, 74817 bytes total.

Archive identity matches the recorded package identity. Each member path is
recorded in ADAPTIVE_MESH_M2_REPORTS.csv, not inferred from directory existence.
The complete report bytes were parsed and preserved, with no head limit or
truncation. All original report schemas contain status, section, spectral,
ranges, interpretation, buffer and continuum_comparison. The six ranges are
identical across sections. Status remains the original historical PASS.

For this checkpoint the exact authenticated archive was read again locally to
preserve the already reviewed records. Python tarfile streamed only named
`<package>/inputs/<registered-section>/NUMERICAL_VALIDATION.json` members, each
less than 512 KiB. No path-based tar extraction was used. Each destination was
constructed from the frozen section list; an existing changed evidence file
would be rejected. SHA-256/size equality was verified after copying. No array,
RDS, checkpoint, mesh, archive or image was copied. This is reacquisition of
reviewed evidence, not an expansion of legacy inspection.

The other 30 selected metadata captures total 142772 bytes. Together with the
reports, verbatim evidence is 217589 bytes (under 2 MiB). Root .gitattributes
already marks `docs/recovery/evidence/** -text`, preserving historical bytes.
Source-code files, environments and all large artifacts remain outside Git.
The local evidence .gitattributes recognizes original CRLF in historical JSON
and original extra EOF blank lines in the two consolidation notes for Git
whitespace checks. The bytes are not normalized to silence diagnostics; authored
documents retain strict whitespace checking.

## Commands and verification

The checkpoint used the existing interpreter, without installations:
`C:\Users\Data Viz\anaconda3\python.exe -B`.
An ignored workspace helper `artifacts/mesh_recovery_checkpoint/build_receipt.py`
performed metadata-only acquisition: hashlib SHA-256 in 1-MiB blocks;
tarfile `r|gz` member listing and exact-member streams; json.loads full parsing;
Path.read_bytes/write_bytes for named metadata; csv.DictWriter LF tables. It did
not import historical source or execute R. The exact original/destination paths
and expected hashes are fully preserved in the inventory tables; the ignored
helper is not required to interpret or authenticate this receipt.

The associated ignored validation helper checks all report/capture sizes and
hashes, source identities, fixed historical JSON fields/types, finite metrics,
section/order/range consistency, derived extrema, manifest and B3 certificate
links, evidence/decision table schemas, documentation links and credential
patterns. Git diff checks and a staged-file/blob review check that only these
documents/tables and small metadata entered the commit. No new fit or numerical
test was run; arithmetic aggregation is not a scientific validation rerun.

## Limitations carried forward

Documented visual approval is not an original user transcript. Source availability
and execution attribution differ. The 19 report hashes authenticate historical
results, not a rerun of their arrays. Their 256-row maximum covariance sample and
six range points do not establish global or prior-wide continuum fidelity.
No buffer/resolution sweep was recovered. Natural-Neumann behavior is an
assembly-based inference. Flat-baseline shared geometry, units, topology policy,
original September rationale and exact plot/CSV generation remain unresolved.
