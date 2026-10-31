# S00 review amendment: self-contained execution evidence

Status: **accepted by explicit user approval: single-section implementation,
independent validation, S00 equivalence and six-file portability**.
Baseline: `51441c885ecf5f4ac19d10a8b399d7d1ade46e1f`.
Both generated bundles retain their execution-time status as review evidence from
uncommitted code, **not the future all-section S00 production artifact**.
The [review record](review.json) contains exact paths, sizes, hashes, source
identities and results. See the [runner guide](../../SINGLE_SECTION_RESPONSE.md).

## Finding and correction

The previous review implementation required absolute process-log paths in its
temporary attempt directory. That broke the intended six-file bundle boundary.
It is superseded for this review; its prior report and artifact identities are
retained under review.json's `supersedes` field as uncommitted review evidence.

Normalization and transport-readback logs are now embedded as exact base64 bytes
in execution.json. Independent pre-promotion readback evidence is embedded the
same way in validation.json. Every embedded log records encoding, decoded byte
count, SHA-256, UTF-8 replacement-decoding policy, warning lines and the measured
stack-imbalance scan result. No seventh bundle file was added.

Validation authenticates the decoded bytes, recomputes the scan, and rejects
stack-imbalance warnings. It never opens an original log path. Original command,
log and output paths remain non-authoritative provenance strings. Temporary
attempts may be deleted after promotion or retained for debugging; they are not
part of the authoritative artifact boundary.

The normalization core, gene panel, cell ordering, coordinates, centering,
depth, tolerances and package versions are unchanged. Full recorrection still
requires the exact code/configuration, authenticated raw source and isolated R
environment. Removing an attempt directory does not bypass those checks.

## Isolation test

One fresh S00 review bundle was generated from the amended source. Exactly its
six files were copied to a fresh directory outside the build/gate directory:

`C:/Users/Data Viz/Desktop/Anderson_Hail/BSFM_RECOVERY_EVIDENCE/sctransform_isolated_review_20261031/S00__Trem2_5xFAD4`

The complete original `S00-build` directory was renamed within its verified
parent to `S00-build-debug-only`. Its original location and all three recorded
normalization/readback log paths were unavailable during validation. The debug
copy was not supplied to the validator and is optional.

`tests/check_bundle_portability.py` required exactly six files, verified all
original log paths were absent, authenticated the embedded bytes, reauthenticated
the raw source/environment and ran full independent saved-model recorrection and
bundle validation. Every copied file remained byte-for-byte unchanged. The test
passed. The surrounding gate contains optional review/debug evidence, not a
dependency of successful bundle validation.

## Reconfirmed tests and scientific results

| Gate | Result |
| --- | --- |
| Python unit and corruption suite | 46 tests passed |
| Existing R count-validation cases | Seven passed |
| Fresh synthetic fits | Four passed; signatures match accepted pre-refactor results |
| Regenerated S00 fit in this amendment | One, passed |
| Isolated six-file full validation | Passed with all original logs absent |
| Accepted S00 corrected-count/log1p equality | Exact |
| Fitting cells, gene order and effective arguments | Exact accepted equivalence |
| All five accepted R semantic hashes | Identical |
| Existing response/centering mutation tests | Passed |

New tests reject changed embedded bytes, SHA-256, byte count, encoding, base64
and warning-scan results. Embedded stack-imbalance warnings fail even with a
correctly recomputed log hash. Tampered independent-readback evidence also fails
when the outer validation-file hash in the manifest is recomputed. A unit test
forbids filesystem opens during embedded-log authentication. Existing execution
checks now pass after their original log is deleted. Copy-isolation is covered
by a small metadata fixture and the unmocked real S00 integration test.

| S00 measurement | Result |
| --- | --- |
| All input/fitting cells | 20,719 |
| Input/output genes | 300 |
| All-cell matrices | 300 x 20,719 |
| Selected/modeling matrices | 91 x 9,451 |
| MIC / AST / OGC | 2,252 / 3,157 / 4,042 |
| Common depth and effective method | 124; glmGamPoi_offset, SCT v2 |
| Largest centered group mean | 2.7991793280442776e-14 |
| Largest reconstruction error | 4.440892098500626e-16 |
| Largest independent mean-reduction difference | 2.7977620220553945e-14; within combined absolute/relative tolerance |
| Normalization process time | 116.162 seconds |
| Bundle run through promotion | 159.646 seconds |
| Observed R peak working set | 1,331,654,656 bytes (1,269.96 MiB) |
| Actual normalization/readback stack warnings | None |

R process time includes startup; memory is sampled Windows peak_wset, not a
Python-process or whole-machine peak. Tolerances are unchanged: centering
atol=1e-12, reconstruction atol=1e-15/rtol=1e-14, and independent mean reduction
atol=1e-14/rtol=1e-14. Other identity and logical equality checks remain exact.

All canonical logical hashes below are unchanged from the first review bundle:

| Dataset | SHA-256 (little-endian float64, logical C order) |
| --- | --- |
| All corrected counts | `a8cbb438809c69d233130ce05a6407ddc63c8fb18f4dc9896415ff31dc4a147d` |
| All uncentered log1p | `e18cc2a640f056f77e0f1ab4ba64ec7b3cfa55b6b46f2f69f7e2a3b430e05a8a` |
| Selected uncentered response | `17f0f6e0655367b78f1f22647964c632a4401a2d5d21eaaec73a9e7640a8d071` |
| Centered modeling response | `dc0f1ad0f4ea96743a916d04f4102f244bf40952e312c3bcc86cc63bda109a7c` |
| Centering means | `5dc143b179b236832f3605498f682cffb75a422ef260c3cdb998c8f2a17887fd` |

The five accepted R signatures cover model_pars, model_pars_fit, cells_step1,
corrected counts and response. HDF5 and RDS serialization hashes are not equated.

## Six-file inventory

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| response.h5 | 21,102,224 | `df46b5c6ce37a876bf9bb7ab8b43fb87ed4b658de803fde2c018d21ce61ac4bc` |
| fit.rds | 47,689,984 | `1af5af6b5b429b488ac44a3a2910607012285767e45f2e4609c04c4b41ff1473` |
| execution.json | 21,772 | `24809af6935df7557d27bf4b4ec713e85f6c260a5acb1a978b1214adbddb4777` |
| session.txt | 4,276 | `0b3cd55fd7ceb444ba2fcb2fdefa7f5689da57934d37708015ef5a5dc6d92798` |
| validation.json | 19,356 | `c1c8837ec3442394ff805e2d662ddb379eaac6042b03c24fff076b0968501474` |
| manifest.json | 11,306 | `80859dfe0d77eec989126707ae4f63b58a34180c9f2f08196363ce24bad3b06a` |

The normalization log contains 1,058 original bytes; each of the two readback
logs contains 71 bytes. All three embedded byte counts/hashes authenticate and
all decoded warning scans are clean. Exact log records and integration evidence
hashes are in review.json. Matrices, fitted models and full evidence remain
outside Git; only source, tests, frozen configuration, documentation and small
aggregate review metadata are included in the accepted change.

Neither this bundle nor the superseded bundle is the future all-section S00
artifact. The other 18 sections, multi-section launcher, mesh, GP initialization,
holdout preprocessing and HPC execution remain untouched. Coordinates remain
source_native, and full-data artifacts remain ineligible for primary holdout
scoring. The user approved committing this bounded gate; no multi-section
orchestration exists and no remaining-section execution is authorized.

Precommit verification after acceptance reran all 46 Python tests, seven R
count-validation cases, four fresh synthetic fits, saved-object R readback,
isolated six-file validation and accepted S00 equivalence: all passed.
Synthetic semantic hashes were unchanged; no real section was refitted.
The small review record includes hashes of these new external test records.
