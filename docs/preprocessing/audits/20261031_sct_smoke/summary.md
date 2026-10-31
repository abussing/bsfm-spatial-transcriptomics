# SCT synthetic validation and bounded S00 smoke

Date: 2026-10-31. Status: **accepted; bounded implementation and evidence approved by the user**.
Execution baseline: `f7d40588840887953b2cda2c562e58a21a9fa1dd`. The runs
preceded the implementation commit and are identified by producer source hashes.
The [manifest](manifest.json) records exact commands, implementation hashes,
external locations, sizes, output hashes, settings, warnings and scope limits.

| Run | Input/fitting cells | Input/output genes | Common depth | Wall seconds | Observed peak working set (MiB) |
| --- | ---: | ---: | ---: | ---: | ---: |
| Synthetic A, first | 240 / 240 | 300 / 300 | 662 | 9.83 | 931.02 |
| Synthetic A, repeat | 240 / 240 | 300 / 300 | 662 | 9.63 | 924.64 |
| Synthetic B, first | 320 / 320 | 300 / 300 | 662 | 9.42 | 918.07 |
| Synthetic B, repeat | 320 / 320 | 300 / 300 | 662 | 9.63 | 915.92 |
| S00 full section | 20,719 / 20,719 | 300 / 300 | 124 | 32.47 | 1,265.55 |
| S00 subset, first | 1,024 / 1,024 | 300 / 300 | 124 | 9.83 | 992.03 |
| S00 subset, repeat | 1,024 / 1,024 | 300 / 300 | 124 | 11.03 | 993.11 |

Every run recorded effective `glmGamPoi_offset`, exact actual fitting-cell
identity/order, finite nonnegative integer corrected counts, a finite response,
deterministic repeated `correct_counts`, and zero difference for
`SCT/data = log1p(SCT/counts)`. An independent scalar NB reconstruction also
matched the corrected counts at the requested depth. All seven fit logs were
free of warnings, including stack-imbalance warnings.

Synthetic raw medians were 662 and 1,766; their independently calculated minimum
662 was applied to both models. Fresh-session repeats matched all five semantic
hashes: initial parameters, regularized parameters, actual fitting cells,
corrected counts and response. The S00 subset repeats matched likewise. A
second full-S00 fit was not performed.

S00 used the accepted raw H5AD fingerprint and preserved all 20,719 eligible
cells and the original 300-gene order. SCT initially estimated parameters for
298 genes under its v2 gene rules, then supplied models and corrected outputs
for all 300. This is model-internal eligibility, not a selected modeling panel.
The full corrected-count and uncentered-response matrices are 300 x 20,719.
Readback of saved RDS artifacts confirmed layer equality, correction-depth
metadata, original RNA counts and exact recorrection from the saved model.

Frozen runtime: R 4.5.3; Bioconductor 3.22; Seurat 5.4.0;
SeuratObject 5.4.0; sctransform 0.4.3; Matrix 1.7-4; glmGamPoi 1.22.0.
See [S00 session](S00-session.txt), [effective arguments](S00-effective-arguments.json),
[installed session](installed-session.txt) and the
[environment build report](../../../environment/SCTRANSFORM_ENVIRONMENT_BUILD.md).

Artifacts remain under:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\sctransform_validation_20261031_attempt1\S00-full\`.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `corrected-counts.rds` | 1,576,159 | `4c9b6a2f607ab7fc23da3651d28d1b1733b3f19e398302d82dbda8ab0ff5ba49` |
| `log1p-response.rds` | 1,556,748 | `a678cf6155b9553763900afe3f121f2ddf29aa3a4c77bdcc0d05ce29f4d781fa` |
| `fit.rds` | 47,689,983 | `5036e6265e3b36a188998509fa5b397463f4ec14ba9b593d266d4a2541ece468` |
| `assays.rds` | 5,735,475 | `02810adf020ade15f02ea3f31325386fe49a8d223018c40527b9b82fc236a099` |

No other section was normalized. There was no cell-type or 91-gene selection,
response centering, GP initialization, HPC execution or holdout validation.
No frozen version or scientific choice was amended during this build. The
earlier environment-loading diagnostic emitted stack-imbalance warnings in a
mixed-order loading loop; individual namespace loads and all actual validation
runs did not. Its cause remains unresolved, so this result certifies the
bounded tested execution path, not every possible use of this environment.
