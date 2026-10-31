# Bounded canonical SCT validation

This runner implements the normalization portion of the
[scientific decision](../decisions/SCTRANSFORM_DESIGN.md) in the
[frozen environment](../decisions/SCTRANSFORM_ENVIRONMENT.md). It is a bounded
validation tool, not the approved all-section production runner. It contains
no historical BSFM implementation code.

The 2026-10-31 assignment authorizes environment acquisition, synthetic fits and
a conditional S00 smoke before review/commit. It supersedes the earlier local
smoke requirement for a committed run specification. This exception applies
only to this local validation; the HPC committed-specification rule remains.
The [validation specification](../../environment/sctransform/validation-spec.json)
records seeds, fixture, resource limits and repeat scope. Runtime manifests
identify the implementation, which was uncommitted at execution, by file hashes.
The user has now accepted this completed bounded gate. No remaining-section,
holdout, panel-selection, centering, GP or HPC execution is accepted by this gate.

## Transformation and checks

1. Read aligned raw counts, cell IDs and all 300 measured gene IDs. For S00,
   rehash the H5AD against the accepted fingerprint, use the frozen sample plus
   fine-label selector, and verify the accepted 20,719-cell ordering and median.
   Materialize only the S00 expression matrix; CSC storage may require bounded
   column scans. Hashing reads the whole file as bytes.
2. Call Seurat's matrix-dispatch `SCTransform` with explicit v2,
   `ncells=N`, `n_genes=NULL`, `return.only.var.genes=FALSE` and seed 1448145.
   Require `glmGamPoi_offset`, the depth-only formula and exact agreement of
   returned `cells_step1` IDs/order with the supplied cells.
3. Disable the wrapper's initial corrected-count calculation. Call
   `sctransform::correct_counts` directly on the fitted model and original raw
   counts with explicit `scale_factor=D`. Repeat correction and independently
   reconstruct its NB mean/variance calculation at D; require identical rounded,
   nonnegative counts. This avoids making an unused section-median response.
4. Construct final SCT/counts and SCT/data, with exactly one `log1p` applied to
   final corrected counts. Check both extracted layers, their axes and exact
   numeric equality. Preserve RNA/counts unchanged, fitted models separately,
   and the SCT model's correction-depth metadata. No residuals become Y.

SCT gene estimation retains its `min_cells=5` rule and v2 Poisson handling.
All 300 measured genes enter the fit and depth calculation; gene-model
availability is reported. There is no 91-gene or cell-type selection. The
residual matrices are neither centered nor scaled here; their clipping settings
are recorded separately and do not define the exported response.

The public library functions and returned fields were checked against pinned
primary source: [Seurat matrix dispatch](https://github.com/satijalab/seurat/blob/083a1b0d6c7732f2f116883885d79d6214ce180f/R/preprocessing.R),
[SCT assay/model accessors](https://github.com/satijalab/seurat/blob/083a1b0d6c7732f2f116883885d79d6214ce180f/R/objects.R),
[vst fit records](https://github.com/satijalab/sctransform/blob/49e35b5aeb76a602910207cbfde1561093340be3/R/vst.R),
[correct_counts](https://github.com/satijalab/sctransform/blob/49e35b5aeb76a602910207cbfde1561093340be3/R/denoise.R).

## Synthetic and S00 gates

The deterministic synthetic fixture has two sections, 300 genes each, with
240 and 320 cells and unequal depth distributions. Python computes the two raw
medians and their minimum independently of the R correction. Each fit runs in
two fresh R processes. Numerical model parameters, actual fitting-cell IDs,
corrected counts and responses must have identical semantic hashes. Timestamps
and complete object serialization are not compared as scientific output.

S00 is reached only after every synthetic check passes. The runner fits S00
once at the accepted full-data depth 124, then repeats two fits of a fixed,
evenly spaced 1,024-cell S00 subset at the same depth. The subset tests
repeatability only: it is not a replacement for the full response or a claim
that a full S00 fit was repeated. The remaining 18 sections are never fitted.

Each R process is limited to 900 seconds and an observed 8-GiB working set.
The actual `bin/x64/Rscript.exe` is launched so Windows `peak_wset` measures
the fitter, not its wrapper. Sampling occurs every 0.2 seconds. This is a
process working-set observation, not a whole-machine or Python-extraction peak.

## Running and output contract

Use the existing Python interpreter with NumPy, h5py and psutil (the optional
`validation` dependency). The runner never installs packages. From the checkout:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m bsfm.preprocessing.sct_smoke `
  --environment '<external-environment-root>' `
  --output-dir '<fresh-external-validation-directory>' `
  --raw-source '<accepted-H5AD-path>'
```

Omit `--raw-source` for synthetic validation only. Output directories inside
the repository, including ignored directories, are rejected by this bounded
runner. Existing output directories are rejected. Failure preserves a failed
manifest and prevents progression to S00; it is never relabeled as a pass.

| Artifact | Schema / contents |
| --- | --- |
| `input.json` | `bsfm.sct-validation-input.v1`: dimensions, ordering hashes, source identity and payload hashes. |
| `counts.f64` | Little-endian float64, original counts in cell-major order; R interprets the bytes as genes x cells. |
| `genes.json`, `cells.json` | Ordered identifiers, external only. |
| `fit.rds` | Full fitted vst result, effective arguments, actual fitting cells, gene availability and model parameters. |
| `corrected-counts.rds` | Sparse genes x cells corrected-count matrix with ordered dimnames. |
| `log1p-response.rds` | Sparse genes x cells uncentered log1p response with matching dimnames. |
| `assays.rds` | Seurat object preserving RNA/counts and final SCT/counts/data with model metadata. |
| `report.json` | `bsfm.sct-validation.v1`: assertions, semantic hashes, versions, settings, warnings and output sizes/SHA-256. |
| `*.process.json`, `*.log` | Exact interpreter argument vector, exit status, elapsed time, memory observation and external log hash. |
| `run-manifest.json` | `bsfm.sct-smoke.v1`: implementation hashes, invocation, environment lock identity, every gate and process report. |

Cell IDs, count payloads, models and full logs stay outside Git. Only aggregate
validation reports and references/hashes are review candidates. Depth 124
remains a full-data value and is not an approved holdout-training depth.
