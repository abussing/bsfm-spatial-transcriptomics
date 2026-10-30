# Raw-input preflight

The reusable Python preflight implements the input-audit portion of the
[frozen SCTransform design](../decisions/SCTRANSFORM_DESIGN.md). It does not fit
SCTransform, transform expression, select the 91-gene modeling panel or prepare
BSFM responses. No legacy implementation was copied.

## Running from the checkout

Python >=3.10, NumPy >=1.24 and h5py >=3.8 are declared in `pyproject.toml`.
The tested existing environment is Python 3.13.5, NumPy 2.1.3 and h5py 3.12.1.
No dependency installation is required in that environment. These are Python
preflight dependencies; they do not satisfy the separate R environment gate.

From the repository root, select an interpreter with those dependencies:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location) 'src')
python -m unittest discover -s tests -v
python -m bsfm.preprocessing.raw_preflight '<raw-source.h5ad>' `
  --output-dir artifacts/sctransform_preflight/<fresh-audit-name> `
  --chunk-rows 4096
```

Optionally append
`--historical-ledger docs/recovery/SCTRANSFORM_B6_SECTION_RECIPES.csv`
to compare aggregate counts with B6. Historical evidence is not required for
the canonical audit and never determines eligibility or correction depth.

Use the chosen interpreter's absolute path if `python` resolves to a different
environment. The input path is always an argument. The CLI never installs
packages. An installed distribution also exposes `bsfm-raw-preflight`.
Use a fresh Git-ignored or external output directory; existing directories are
rejected to preserve prior evidence. Keep every generated report outside Git
pending review. No code paths write to the input H5AD.

## Input and selection contract

- Raw counts: `layers/RNA`, oriented cells by genes. Dense, CSR and CSC H5AD
  storage are supported. Sparse indices must be sorted and unique within each
  compressed vector; malformed or ambiguous storage fails without repair.
- Identities: the index named by each `obs`/`var` dataframe's `_index` attribute
  (fallback name `_index`). IDs must be nonempty and unique. Exactly 300 genes
  are required; their existing order is preserved and fingerprinted.
- Section selection: decoded `obs/sample` **and** decoded `obs/gen_fine`.
  The bundled `src/bsfm/preprocessing/sections.json` contains all 19 exact
  selectors. Its provenance is committed B4 metadata, capture lines 222–241,
  with the original registry hash recorded. Category positions are not used
  as identities. Both S12 sections share a sample but have distinct fine labels.
- Cell types: decoded `obs/cluster_coarse`; `Mic` maps to MIC, `AST` and `OGC`
  retain their names, and all other nonempty labels participate as other cells.
- Coordinates: finite numeric `obsm/spatial`, shape `(n_cells, 2)`.

H5AD string arrays and categorical columns are decoded according to the
[AnnData file format](https://anndata.readthedocs.io/en/stable/fileformat-prose.html).
Count reads use bounded HDF5 slices through
[h5py datasets](https://docs.h5py.org/en/stable/high/dataset.html).
The preflight does not read `X`, other layers, embeddings, fitted objects or
unrelated metadata. SHA-256 necessarily reads the complete file as opaque bytes.

## Eligibility, summaries and failures

Every stored raw value is checked for finiteness, nonnegativity and exact
integer value. No rounding or tolerance is applied. Structurally invalid cells
and valid zero-total cells are excluded explicitly. Invalid spatial coordinates
or missing cell-level type/section metadata also exclude a cell. There are no
additional expression thresholds. Reasons can overlap; the excluded-cell union
is reported separately to prevent double counting.

Dataset-wide identifier/shape corruption or absent required fields raises a
contract failure. Unregistered section combinations or sections with no eligible
cells withhold the common depth. Invalid individual cells produce
`review_required` with an explicitly provisional depth from the remaining
eligible population. This permits the approved structural exclusions while
requiring findings to be reviewed before accepting an input.

Counts are accumulated exactly in uint64. Individual values or totals above
2^53 are flagged and excluded before float64 summaries; with 300 genes,
accumulating supported individual values cannot overflow uint64. Quantiles use
NumPy's explicit `linear` convention: min, 1%, 5%, 25%, median, 75%, 95%, 99%, max.
An even-size median averages the middle two totals. The proposed full-data
depth is the minimum of all 19 eligible section medians, using all 300 genes
and all eligible cell types. This depth is not a holdout-training depth.

The B6 ledger comparison uses **all selected cells before exclusions** and their
MIC/AST/OGC total, matching historical count semantics. Eligible counts are
reported separately. Historical mismatches are findings, never targets used
to alter eligibility or depth. When supplied, the ledger must contain exactly
the same 19 section IDs. Without it, historical comparison fields are null in
JSON, blank in CSV and labeled `not compared` in the summary.

Exit status: 0 = pass; 1 = review required; 2 = failed contract/read/report.
Schema failures report the reason on stderr and do not create a successful
audit. Completed scans with missing eligible sections produce reports with
status `fail` and null depth. Reports are deterministic for the same input,
paths, implementation, dependencies and options; they contain no timestamps.
File size and modification time are checked before and after the audit to
detect ordinary concurrent changes. This is not a filesystem snapshot; audit
an immutable source rather than a file being edited concurrently.

## Artifacts and provenance limits

| Artifact | Contents |
| --- | --- |
| `audit.json` | Versioned `bsfm.raw-preflight.v1` audit, input bytes/hash, schema/order fingerprints, runtime/module/registry identities, eligibility, 19 sections, findings and depth. |
| `sections.csv` | One row per full section identity; all/eligible counts by type, exclusions, total-count quantiles, ordered-cell fingerprints and B6 count deltas. |
| `exclusions.csv` | Local-only zero-based source row, section and exclusion reasons. Rows resolve to cell IDs in the fingerprinted H5AD. No expression values. |
| `summary.md` | Human-readable counts, depth, optional historical agreement, limitations, interpreter and CLI argument vector. |
| `manifest.json` | Small review candidate: aggregate/schema/input/code/runtime identities, CLI invocation and byte sizes/SHA-256 of the four reports. Not automatically promoted into Git. |

Ordered identifier hashes encode each UTF-8 identifier as its uint64
little-endian byte length followed by its bytes, in source order. The audit
preserves identity/order fingerprints without exporting cell-level identifiers
or expression values into repository files. Exclusion row numbers remain
data-specific local artifacts. The matrix is never loaded in full; metadata,
per-cell totals and masks are held in memory, and expression reads are bounded
by `chunk_rows * 300` entries. Exact section quantiles use per-cell totals.

A file fingerprint plus matching schema and historical counts does not prove
independent origin authenticity. No independently trusted raw-file checksum or
authoritative ordered gene list has been supplied for comparison. The first
audit establishes a content identity for review. Approving that identity for
future runs is distinct from certifying the historical normalization or any
newly generated SCT response. The fixed 91-gene panel is a later check.

The [accepted 2026-10-30 aggregate record](audits/20261030_raw/summary.md)
freezes the project-adopted fingerprint and full-data depth 124 by explicit
user approval. Only its manifest, section CSV and summary are tracked. The
manifest's `audit.json` and `exclusions.csv` hashes refer to local files in the
ignored output directory recorded by its invocation, not to missing Git files.
Repository text uses LF via `.gitattributes`; historical captures retain their
original bytes. Runtime and source hashes identify the tested implementation.
