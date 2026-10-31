# Canonical SCTransform full-data v2 production receipt

Status: **implemented and production-validated; all 19 sections complete/pass**.
Execution and this registration were explicitly user approved. This receipt
registers completed artifacts; it does not authorize another run or downstream work.
Generating commit: `6eb672bebbaf5cde6c9d50391aac275a210832a6`. The later documentation commit
registering this receipt is not the generating commit.

## Artifact identities and location

The external artifact root is **machine-local**, not shared storage or a Git backup:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2
```

The raw input and isolated environment paths below, and every absolute path in
the copied metadata, are also machine-local. Relative section manifest paths
resolve under that external root, not inside this audit directory.

| Preserved metadata | Bytes | SHA-256 |
| --- | ---: | --- |
| [run-manifest.json](run-manifest.json) | 48980 | `03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f` |
| [run-specification.json](run-specification.json) | 7905 | `63175bd28c0b4b8abde349e27816904a932831bcc52feda978d9e0197ba34b0d` |
| [sections.csv](sections.csv), derived aggregate audit | 8343 | `07b353ad59db0ff1d6cd639bdaf72009f603656c79f2237c1adccee80e2d1e18` |

Both JSON files are byte-identical copies, validated under the existing
[production-manifest schema](../../../../schemas/preprocessing/production-manifest.schema.json)
and [production-specification schema](../../../../schemas/preprocessing/production-specification.schema.json).
No competing receipt JSON schema is introduced. The CSV is a derived summary,
not a replacement completion manifest. Its execution/validation hashes link each
row to the external section manifest authenticated by the copied run manifest.

The metadata contain only expected provenance paths, source file-stat identities,
code/configuration hashes, timing/resource observations and completion records.
Credential-pattern and structured-content checks passed. Local device/inode and
file-stat fields are provenance observations, not portable retrieval identifiers.
No cell-level identifiers, expression values, process-log content or credentials
are copied. Matrices, fit objects, libraries, archives and section bundles remain external.

## Source, environment and configuration

Raw source (machine-local): `D:\johnston_brain\Johnston_MERFISH_Data.h5ad`.
Size: 5,483,600,151 bytes. Authenticated SHA-256:
`d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`.
Whole-source authentication passed at process start and closure, with unchanged
source stat identity. This remains the project-adopted content fingerprint,
not an independently supplied upstream checksum.

Environment (machine-local): `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031`.
Frozen R 4.5.3 / Bioconductor 3.22 target; runtime package checks confirmed
Seurat 5.4.0, SeuratObject 5.4.0, sctransform 0.4.3, Matrix 1.7-4 and glmGamPoi 1.22.0.
Every fit recorded effective method `glmGamPoi_offset`; no fallback occurred.
The deliberate glmGamPoi amendment is preserved in the
[environment decision](../../../decisions/SCTRANSFORM_ENVIRONMENT.md).

Frozen inputs are `config/preprocessing/single-section-run.json` and
`config/preprocessing/production-run.json`, the panel, section registry, bundle
specification and environment locks. Exact configuration contents, source-code
hashes and schema identities are preserved in the copied run specification.
Production-policy SHA-256: `094aa8b79b7ba70cb1fb209fea1a39638476785e6dc5739666c6aca120eb97f9`.

| Identity | SHA-256 |
| --- | --- |
| `panel_registry_sha256` | `85707ff1db48b697de58f2b0260daef2d40d6ac6a7710cdfa5e87da422c14f98` |
| `panel_order_sha256` | `48e934a62161d7fb69e3abb3e636a979660b6e1b62cbacdcec929c2584d8bfa8` |
| `section_registry_sha256` | `f336de10e58e0b2269ceed62c4c6c454af9956f9460c9097b3d42c7ccf368166` |
| `bundle_spec_sha256` | `fa451ab856eaa9d7b05261ac6d79dcbdbc171a8ee391610733426938b45c7610` |
| `run_spec_sha256` | `64eae68d04864b29746e31fb0d4367f7488e005310bf90614009c84502d9de83` |
| `environment_source_lock_sha256` | `2c258eef6b3284118f82e062e301019ae0c7b434cafad2958f4c8b003ca5c281` |
| `renv_lock_sha256` | `b3ab89dc1bcfe7cd082b9c334e425d02cb296e468f208c22ff777a182943f3b9` |

Here `identities.run_spec_sha256` is the single-section configuration hash;
the top-level `run_spec_sha256` identifies the copied production run specification.
The source/renv locks identify dependencies; they are not a hash of every installed
library file. Exact session/package checks are in external execution records.

## Measured production results

- 19/19 sections passed in frozen registry order, including both distinct S12 sections.
- 432,794 all-section cells, 300 genes; 187,100 modeled MIC/AST/OGC cells, 91 genes.
- Each all-cell matrix is 300 x N; each modeling matrix is 91 x M. Every section's
  N, M, type counts, runtime, peak R memory and validation maxima are in sections.csv.
- Correction depth is 124 for every section. All eligible cells and all 300 genes
  were supplied; correction precedes the fixed panel/type selection.
- Response is exactly one log1p of common-depth corrected counts, followed by one
  section/type/gene centering operation; no variance scaling or second logarithm.
- Maximum centering residual: 5.921414647059861e-14.
- Maximum reconstruction error: 4.440892098500626e-16.
- Mean comparisons: 5,187/5,187 passed the frozen roundoff-aware bounds;
  maximum discrepancy/bound ratio 0.019363281968369995.
- All five semantic signatures matched fitting, transport readback and independent
  saved-model recorrection for every section. Exact payload/layer, axes, selection,
  coordinates, centering/reconstruction and provenance checks passed before promotion.
- All 19 six-file bundles passed deep validation before promotion and fast
  authenticated validation afterward and at closure. Fast checks were repeated
  read-only at the generating commit before writing this receipt; they did not refit.
- No stack-imbalance warning occurred in the recorded normalization/readback processes.
- Concurrency remained 1. The 7 GiB RAM and 10 GiB disk resource gates passed.
- Recorded session: `2026-10-31T20:16:02.923177+00:00` to
  `2026-10-31T20:56:24.736646+00:00`; 2421.813469 seconds (40 min 21.8 s), including
  closure but excluding initial whole-source authentication before session start.
- Total run-root file size: 1,446,987,796 bytes (1.347612400 GiB).
  Section bundles: 1,446,863,351 bytes.
- Per-section runtime is the ledger's `deep_before_promotion_plus_fast_after`
  elapsed time; it excludes subsequent cleanup. Peak R memory is the maximum
  recorded main-R-process working set across fitting and both readbacks, sampled
  every 0.2 s with Windows peak_wset. It excludes Python and combined process-tree
  overhead. The largest recorded R peak is 1,723,596,800 bytes.

## Fresh execution, closure and immutable v1

The v2 destination was confirmed absent before the approved command. One new
process executed one fresh attempt per section from the authenticated raw H5AD;
there were no resume checks, skipped sections, reused fits or failed attempts.
All 19 sections, including S00 and S01, were recomputed from raw counts. No v1
artifact was copied, promoted, hard-linked or otherwise reused as production input.
Execution records identify v2-specific attempts and raw inputs; all finalized
files have one filesystem link. These records corroborate the observed fresh launch.
Successful temporary attempts were removed only after durable promotion/checkpoint.

The final manifest reports `status=complete`, `pass=true`; the external ledger
reports `complete`, with final source authentication and no hidden failures.
External `run-ledger.json`: 51202 bytes,
SHA-256 `89372a119bb2d2bce5b29da3dfdd3a24fdf02b16d2959c84d6035e95bdb062a7` (referenced, not copied).

V1 remains **failed and immutable**, at machine-local `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v1`.
All 51 file sizes and SHA-256 values were rechecked against the pre-correction
inventory and remain identical; no final v1 run manifest exists. The inventory is
machine-local `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\sctransform_roundoff_audit_20261031\v1-before.json` (11574 bytes,
SHA-256 `3c64d06788e9786b2d81925d98d38df6d1cfa209cfbbd253fc1b481c7e436bce`), already referenced by the
[roundoff audit](../20261031_mean_roundoff/review.json). Neither v1 nor v2 was
modified while registering this receipt.

## Scope and later validation

These are full-data artifacts: `preprocessing_regime=full_data`,
`primary_holdout_scoring_eligible=false`, `fold_id=null`. They are **not eligible
for primary holdout scoring**. Future holdout experiments require separately
specified training-only fitting, depth estimation and centering populations.
Panel-selection independence remains unestablished. Coordinates remain unchanged
in center_y/center_x order with source_native units, not verified microns.

The generating code identity is immutable. Existing validators require that
exact checkout for artifact validation; a later documentation commit must not
be substituted for it or bypass provenance checks. This receipt establishes
canonical full-data preprocessing, not historical mixed-recipe comparability,
GP initialization, mesh correctness, BSFM modeling or HPC execution.
