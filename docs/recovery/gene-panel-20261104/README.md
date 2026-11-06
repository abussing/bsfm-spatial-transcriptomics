# Recovered 91-gene selection rationale

This reference records the provenance of the frozen panel and its regression
rule. It does not define a universal panel or certify all upstream screening fits.

## Actual final rule and reason

The saved `GENE_PANEL_CONTRACT.json` and `freeze_gene_panel.py` agree:

1. Use the screening GP spatial fraction: signal variance divided by signal
   variance plus white-noise variance.
2. Require spatial fraction >=0.10 in at least two distinct animals within at
   least one cell type (Mic, AST or OGC). Recurrence is within the same type,
   not two animals qualifying in different types. Technical sections do not
   count as independent animals.
3. Do not select using genotype or require a WT-specific effect.
4. Do not gate on the auxiliary random-location held-out prediction gain.
   The recorded reason is missing held-out scores in part of the reused-fit
   branch: interpreting missing scores as failures removed microglial genes
   and biased the panel. Missing scores are not evidence of poor prediction.

This selects recurrent spatial expression, rather than genes chosen because
deep BSFM beat flat BSFM. The rule yields 91 genes, ordered alphabetically;
39 have AST as their recorded best-supported type, 38 Mic and 14 OGC.

## Independent verification

The saved animal-summary SHA-256 matches the production contract. An independent
standard-library CSV filter, without executing the historical script, reconstructed
the threshold and distinct-animal recurrence from 2,515 rows covering 15 animals.
Its ordered 91 genes equal all of:

- the saved production contract's ordered list;
- `FROZEN_GENE_PANEL.csv`;
- the current `config/preprocessing/modeling-panel.json` registry.

`VALIDATION.json` records exact source paths, hashes and capture names. Captures
are evidence, not an alternative source of runnable pipeline code. The complete
source capture also remains on HPC at
`/work/abussing/bsfm-consolidation/evidence/gene-panel-recovery-20261104.json`.

## Earlier screening and remaining limits

The local historical `E:/johnston_brain/artifacts/GENE_REVIEW_20261004/`
`screen_all_genes_expression.py` and `all300_expression_screen/QC.json` describe
an earlier expression filter: >=30% nonzero, 90th percentile >=1 in SCT log1p
units, finite and nonconstant, together within a type/section, recurring across
at least two animals. That stage produced 137 eligible genes, not the final 91.
The local extension source aggregates technical sections by median for each
gene/type/animal. These upstream observations have not been independently
reproduced from all source matrices in this recovery.

The previous canonical panel decision intentionally froze names/order without
establishing this final selection rationale. The newly recovered evidence fills
that documentation gap; no historical user conversation or threshold-selection
optimization has been recovered. Independence from future held-out expression
remains unestablished.

## Screening implementation provenance

The reusable GP screen was recovered from `review.py`, `fit_one`, lines 167-213,
in `E:/johnston_brain/artifacts/GENE_REVIEW_20261004/`, source SHA256
`8b590e72c4333a1241d5d3fca110cabc1b0cb43da7b5d3b8a8d96788b953173f`.
Its Matérn-2.5 kernel, bounds, standardization, jitter, optimizer settings and
fixed per-group sampling are preserved. Technical-section median aggregation is
also captured in `historical_gp_extension.py`. These source identities document
lineage; historical scripts are not alternative runnable entry points.

For a new dataset, use the [dataset guide](../../preprocessing/DATASET_CONTRACT.md).
Declare response units, modeling groups and whether biological replication exists.
Do not transfer response-unit thresholds blindly or invent independent animals.
