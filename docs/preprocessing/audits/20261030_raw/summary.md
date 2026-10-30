# SCTransform raw-input preflight

Status: **pass**.
Source SHA-256: `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`.
Size: 5483600151 bytes.
Cells: 432794; eligible: 432794; genes: 300.
Proposed common depth: **124.0**.

| Section | All | Eligible | MIC | AST | OGC | Other | Zero | Median | B6 match |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| S00__Trem2_5xFAD4 | 20719 | 20719 | 2252 | 3157 | 4042 | 11268 | 0 | 124.0 | True |
| S01__5xFAD4 | 24087 | 24087 | 3617 | 3601 | 4720 | 12149 | 0 | 178.0 | True |
| S02__Trem2_4 | 26716 | 26716 | 1019 | 3578 | 4352 | 17767 | 0 | 133.0 | True |
| S03__Trem2_5xFAD3 | 22868 | 22868 | 2164 | 3600 | 4793 | 12311 | 0 | 302.0 | True |
| S04__WT3 | 17863 | 17863 | 838 | 3238 | 4232 | 9555 | 0 | 278.0 | True |
| S05__Trem2_3 | 22539 | 22539 | 1024 | 3678 | 5426 | 12411 | 0 | 319.0 | True |
| S06__5xFAD3 | 22965 | 22965 | 2507 | 3514 | 5366 | 11578 | 0 | 330.0 | True |
| S07__Trem2_5xFAD5 | 18594 | 18594 | 1621 | 2423 | 4010 | 10540 | 0 | 133.0 | True |
| S08__5xFAD5 | 19034 | 19034 | 2299 | 2872 | 3438 | 10425 | 0 | 129.0 | True |
| S09__Trem2_5 | 23223 | 23223 | 918 | 2967 | 5130 | 14208 | 0 | 138.0 | True |
| S10__WT5 | 25307 | 25307 | 996 | 3337 | 5089 | 15885 | 0 | 149.0 | True |
| S11__Trem2_5xFAD1 | 23598 | 23598 | 2845 | 3772 | 4296 | 12685 | 0 | 360.0 | True |
| S12__Trem2_1 | 28532 | 28532 | 1064 | 4407 | 6179 | 16882 | 0 | 335.0 | True |
| S12__Trem2_5xFAD2 | 27741 | 27741 | 3560 | 4488 | 5437 | 14256 | 0 | 387.0 | True |
| S13__Trem2_2 | 14282 | 14282 | 543 | 2059 | 2453 | 9227 | 0 | 328.0 | True |
| S14__WT1 | 24291 | 24291 | 1149 | 3796 | 4479 | 14867 | 0 | 267.0 | True |
| S15__5xFAD1 | 23957 | 23957 | 3008 | 3265 | 4602 | 13082 | 0 | 306.0 | True |
| S16__WT2 | 21030 | 21030 | 1013 | 3213 | 3974 | 12830 | 0 | 282.0 | True |
| S17__5xFAD2 | 25448 | 25448 | 3423 | 3548 | 4709 | 13768 | 0 | 298.0 | True |

MIC/AST/OGC/Other counts above are eligible cells. Quantiles and pre-exclusion counts are in sections.csv.

Findings:

- No contract or historical-count discrepancies found.

Limits:

- No SCTransform executed; no generated response certified.
- No external reference gene list or raw-file checksum authenticated independently.
- The fixed 91-gene modeling panel and R environment are separate later checks.
- Full-data depth only; not approved for training-only holdout preprocessing.

Execution provenance:

```json
{
  "implementation": {
    "module_sha256": "56d0e07fa81366fb6ea91dc8140039367f1aee5b28c2adad1c0597675fb6c749",
    "registry_sha256": "f336de10e58e0b2269ceed62c4c6c454af9956f9460c9097b3d42c7ccf368166"
  },
  "invocation": {
    "argv": [
      "C:\\Users\\Data Viz\\anaconda3\\python.exe",
      "-m",
      "bsfm.preprocessing.raw_preflight",
      "D:\\johnston_brain\\Johnston_MERFISH_Data.h5ad",
      "--historical-ledger",
      "docs/recovery/SCTRANSFORM_B6_SECTION_RECIPES.csv",
      "--output-dir",
      "artifacts/sctransform_preflight/20261030_raw_final",
      "--chunk-rows",
      "4096"
    ],
    "working_directory": "C:\\Users\\Data Viz\\Desktop\\Anderson_Hail\\bsfm-spatial-transcriptomics"
  },
  "runtime": {
    "h5py": "3.12.1",
    "hdf5": "1.14.5",
    "interpreter": "C:\\Users\\Data Viz\\anaconda3\\python.exe",
    "numpy": "2.1.3",
    "python": "3.13.5"
  }
}
```
