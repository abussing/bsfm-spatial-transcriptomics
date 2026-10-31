# All-section production-readiness audit

Checkpoint: `7f5b6042677ea917de4b254c05f319aa715704df`; main = origin/main; clean before and after audit.
Measured at 2026-10-31T19:05:17.623029+00:00. Read-only; no SCT, models, response construction, repository edits or launcher.

## Result: no observed raw-input or min_cells blocker

All 19 registered sections pass the metadata/count contract and all 5,700 section/gene combinations pass min_cells=5. This establishes input eligibility, not successful model fitting or output certification. The ordered 91-gene panel is uniquely present and threshold-eligible in every section; no missing, duplicate or below-five panel gene was found.

Raw source: `D:\johnston_brain\Johnston_MERFISH_Data.h5ad`; 5,483,600,151 bytes; SHA-256 `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`.
One whole-file SHA-256 pass (11.99 s), then one chunked RNA scan (2.36 s; 4,096 rows/chunk). A preceding read-only schema probe read no counts. File size/mtime remained stable. This uses the adopted project fingerprint, not an independent upstream checksum.

432,794 cells, 300 unique genes, 187,100 modeled cells, 15 recorded animal labels. All cells have finite nonnegative integer counts and positive totals. All eight required metadata columns are populated; cell IDs and raw rows are unique; coordinates are finite and exactly equal the unchanged center_y/center_x source columns. Animal/genotype are unambiguous per section; each modeled type is nonempty. All section counts, ordered cell identities and medians agree with the accepted audit; minimum section median remains 124. The two S12 selections remain distinct via sample + gen_fine.

## Measured section table

All-cell matrices have shape 300 x N; selected uncentered/centered matrices 91 x M; centering means 91 x 3. All columns below are measured, not extrapolated. Min300/Min91 are nonzero-cell minima across each gene set. Every section passes the checks above.

| Section | N | MIC | AST | OGC | M | Min300 | Min91 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| S00__Trem2_5xFAD4 | 20,719 | 2,252 | 3,157 | 4,042 | 9,451 | 240 | 531 |
| S01__5xFAD4 | 24,087 | 3,617 | 3,601 | 4,720 | 11,938 | 368 | 1102 |
| S02__Trem2_4 | 26,716 | 1,019 | 3,578 | 4,352 | 8,949 | 356 | 764 |
| S03__Trem2_5xFAD3 | 22,868 | 2,164 | 3,600 | 4,793 | 10,557 | 489 | 2931 |
| S04__WT3 | 17,863 | 838 | 3,238 | 4,232 | 8,308 | 413 | 1378 |
| S05__Trem2_3 | 22,539 | 1,024 | 3,678 | 5,426 | 10,128 | 433 | 1867 |
| S06__5xFAD3 | 22,965 | 2,507 | 3,514 | 5,366 | 11,387 | 723 | 3230 |
| S07__Trem2_5xFAD5 | 18,594 | 1,621 | 2,423 | 4,010 | 8,054 | 276 | 663 |
| S08__5xFAD5 | 19,034 | 2,299 | 2,872 | 3,438 | 8,609 | 209 | 492 |
| S09__Trem2_5 | 23,223 | 918 | 2,967 | 5,130 | 9,015 | 278 | 849 |
| S10__WT5 | 25,307 | 996 | 3,337 | 5,089 | 9,422 | 302 | 1047 |
| S11__Trem2_5xFAD1 | 23,598 | 2,845 | 3,772 | 4,296 | 10,913 | 550 | 2860 |
| S12__Trem2_1 | 28,532 | 1,064 | 4,407 | 6,179 | 11,650 | 620 | 2011 |
| S12__Trem2_5xFAD2 | 27,741 | 3,560 | 4,488 | 5,437 | 13,485 | 670 | 3275 |
| S13__Trem2_2 | 14,282 | 543 | 2,059 | 2,453 | 5,055 | 313 | 987 |
| S14__WT1 | 24,291 | 1,149 | 3,796 | 4,479 | 9,424 | 648 | 2079 |
| S15__5xFAD1 | 23,957 | 3,008 | 3,265 | 4,602 | 10,875 | 645 | 2151 |
| S16__WT2 | 21,030 | 1,013 | 3,213 | 3,974 | 8,200 | 1007 | 2286 |
| S17__5xFAD2 | 25,448 | 3,423 | 3,548 | 4,709 | 11,680 | 756 | 2153 |

[gene_nonzero_counts.csv](gene_nonzero_counts.csv) records every one of the 5,700 counts and the >=5 result, in raw gene order. [sections.csv](sections.csv) includes complete checks, dimensions, raw density, identities and per-section estimates. [audit.json](audit.json) records formulas, measured calibration, bounded attempt inventory and limitations.

## Resources: measured calibration and extrapolations

S00 measured response.h5: 21,102,224 bytes; fit.rds: 47,689,984 bytes; retained successful-attempt files: 409,025,132 bytes excluding the final bundle. File sizes were measured without opening matrices or fitted objects. Its whole-run time was 159.646 s and R-only peak working set 1.240 GiB. Python/system-wide peaks were not measured.

| Section | Est. response MiB | Est. fit MiB | Est. temporary MiB | Est. whole run min | Worker budget GiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| S00__Trem2_5xFAD4 | 20.1 | 45.5 | 390.1 | 2.66 | 5.04 |
| S01__5xFAD4 | 23.6 | 52.9 | 453.5 | 3.09 | 5.53 |
| S02__Trem2_4 | 25.1 | 58.6 | 503.0 | 3.43 | 5.91 |
| S03__Trem2_5xFAD3 | 22.2 | 50.2 | 430.5 | 2.94 | 5.35 |
| S04__WT3 | 17.4 | 39.2 | 336.3 | 2.29 | 4.62 |
| S05__Trem2_3 | 21.9 | 49.5 | 424.3 | 2.89 | 5.30 |
| S06__5xFAD3 | 22.5 | 50.4 | 432.4 | 2.95 | 5.37 |
| S07__Trem2_5xFAD5 | 17.9 | 40.8 | 350.1 | 2.39 | 4.72 |
| S08__5xFAD5 | 18.5 | 41.8 | 358.4 | 2.44 | 4.79 |
| S09__Trem2_5 | 22.1 | 51.0 | 437.2 | 2.98 | 5.40 |
| S10__WT5 | 24.0 | 55.6 | 476.5 | 3.25 | 5.71 |
| S11__Trem2_5xFAD1 | 23.0 | 51.8 | 444.3 | 3.03 | 5.46 |
| S12__Trem2_1 | 27.4 | 62.6 | 537.2 | 3.66 | 6.18 |
| S12__Trem2_5xFAD2 | 27.2 | 60.9 | 522.3 | 3.56 | 6.07 |
| S13__Trem2_2 | 13.5 | 31.4 | 268.9 | 1.83 | 4.09 |
| S14__WT1 | 23.2 | 53.3 | 457.3 | 3.12 | 5.56 |
| S15__5xFAD1 | 23.3 | 52.6 | 451.0 | 3.08 | 5.51 |
| S16__WT2 | 20.1 | 46.2 | 395.9 | 2.70 | 5.08 |
| S17__5xFAD2 | 24.7 | 55.9 | 479.1 | 3.27 | 5.73 |

- response.h5 estimate scales S00 by (600N + 182M), representing the two all-cell and two modeled matrices; fit.rds and temporary storage scale by N. Compression, metadata and gene-expression density can change these sizes. Metadata JSON/session overhead is small and covered by reserve.
- Temporary estimate uses a bounded inventory of the retained S00 attempt: raw transports, normalization artifacts, duplicate fitted object and both readbacks. It is not a measured all-time disk peak. Reserve twice the estimate for each active section.
- Worker planning budget = 2 x measured S00 R peak x N/N0 + 2 GiB fixed Python/metadata allowance + 12 x (300 x N x 8) transient numeric-buffer allowance. These conservative allowances are assumptions, not measured whole-worker peaks.
- Linear sequential total: **55.6 minutes**. Allow roughly **1-2 hours** operationally; this is not a bound. It includes S00's observed hashing/readback costs scaled by N, so cache/I/O and model effects can differ. No other section was timed.
- Estimated total final response+fit storage: **1.34 GiB**; retained attempts across all 19: **7.96 GiB**. With cleanup after each validated promotion and a 2x temporary allowance, estimated disk requirement is **2.38 GiB**. Recommend at least **10 GiB** free for the initial sequential run, plus retained prior evidence (already reflected in current free space). Keeping every attempt costs about 9.29 GiB before extra safety reserve.
- Proposed external destination parent: `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE` on C:. Measured free space **650.31 GiB**. Machine RAM **31.74 GiB**, available **20.19 GiB** at measurement.
- Recommend **concurrency 1**, reserving **7 GiB per worker** (largest formula budget 6.18 GiB) plus **8 GiB for OS/other applications**. Plenty of disk/RAM does not establish validated parallel safety; Python memory and concurrent I/O remain unmeasured.

## Operational risks and boundaries

The largest sections are S12__Trem2_1 (28,532 cells; 1.38x S00), S12__Trem2_5xFAD2 (27,741; 1.34x), and S02__Trem2_4 (26,716; 1.29x). None is twice S00 by cell count. These are the largest expected jobs by dimensions; runtime/compression also depend on count density. No section fails the strict 300-gene contract on the measured min_cells criterion. Actual model availability, numerical checks and warnings remain execution gates.

- No observed raw-data or min_cells blocker for applying the single-section numerical implementation to all 19 sections unchanged. Successful fitting, output genes, warnings, tolerances and limits still require execution validation.
- Current runner requires a fresh destination root per invocation; a single shared existing root is rejected (response_run.py:86). No launcher exists.
- Current runner rehashes the full H5AD in raw_section (response_contract.py:97-99), both before fitting and inside validate_payload (response_run.py:95,114; response_validate.py:131). Nineteen unchanged invocations read 38 full fingerprints (208,376,805,738 bytes) plus section data; separate final validation adds further reads.
- R process limits remain 900 seconds and 8 GiB per process, not a combined Python/R memory bound. Linear normalization estimates are below these limits; actual other-section behavior is unmeasured.
- code_identity execution_authority retains user-authorized local review/uncommitted wording (response_contract.py:83-87); frozen run configuration scope also refers to an S00 review gate. Actual commit/hash are recorded correctly, but future production provenance/authorization wording needs review; this audit changes neither.
- Successful-attempt files may be removed after the promoted six-file bundle and hashes validate. Attempt directories are optional; preserve the final section directory, exact code/configuration, authenticated source and isolated environment. Failed/interrupted attempts must not be treated as complete. No files were deleted.
- Accepted S00 artifacts were made under the previous uncommitted review identity; they are calibration evidence, not the future production S00 bundle. Current validator requires exact code identity, so old review results are not relabeled under the new commit.
- Coordinates remain source_native; full-data outputs remain ineligible for primary holdout scoring. Other-section fit behavior and total process memory remain unmeasured.

Implementation evidence: `sct_core.R:52,61-66` pins/applies min_cells; `response_run.py:25` and `response_validate.py:115` require all 300 outputs. `response_run.py:86,95,114` defines fresh roots and repeated raw loading. `sct_smoke.py:136,162-170` implements R process limits/measurement. `response_contract.py:83-87` records commit/source identities and review provenance wording. The accepted portability report proves original attempt logs are unnecessary; this audit did not repeat normalization or recorrection.

Stop for review before launcher design or production execution. No repository files changed.
