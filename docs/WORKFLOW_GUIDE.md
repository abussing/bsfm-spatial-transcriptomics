# Reusable BSFM workflow: methods, recipes and current gaps

The repository is the scientific and operational reference for new datasets.
A method explains why and implements how; a recipe supplies dataset identities,
groups, units, populations and settings. Regression fixtures test preservation
of a recipe, rather than defining the only possible dataset.

This is the current workflow map, updated 2026-11-04. The complete
new-dataset workflow is **not yet available as one command**. Existing S10 runs
and exact source checkouts remain unchanged.

The core sequence is input, normalization, gene selection, mesh, initialization,
GPU sampling and saved outputs. Extend existing layer interfaces before adding
a wrapper or entry point. Dataset recipes supply identities and choices; they
do not define separate pipelines. Leave-out design and scoring are downstream
experiments, outside the current cleanup. Preserve historical evidence and exact
contracts; update this guide in place rather than adding competing current guides.

## Decision and implementation map

| Stage | Rationale / reusable implementation | Remaining coupling or gap |
| --- | --- | --- |
| Input | [Portable dataset contract](preprocessing/DATASET_CONTRACT.md), hash-pinned read/write and explicit RData adapter; real axolotl readback passes | Johnston raw adapter remains separate; more source formats require adapters |
| SCT | [Accepted design](decisions/SCTRANSFORM_DESIGN.md); `preprocessing/sct_core.R` accepts counts/depth | Extraction, depth policy and 300-gene validators are Johnston-specific; training-only SCT application unfinished |
| Library normalization | `preprocessing.normalization.log_library_size` takes explicit target sum and log base; distinct from SCT | Dense helper only; generic file ingestion and transform manifest needed |
| Existing response | Portable dataset manifest declares method/units/population/evidence; no automatic transformation | Original fit-population independence must be established separately |
| Expression eligibility | `preprocessing.gene_selection.expression_eligible`: explicit detection, level and nonconstancy thresholds | Thresholds depend on response units; no implicit transfer between normalization methods |
| Spatial selection | [Recovered rule](recovery/gene-panel-20261104/README.md); `select_spatial_genes` and CLI reproduce all 91 genes | `spatial_screen` supplies GP fits and technical-section medians; unknown biological replication requires an explicit policy |
| Centering | `dataset.prepare_response` exports named training/scoring arrays using training-only means; arbitrary group/gene counts pass sampler contract | Single-sample preparation; mesh and GPINIT still separate |
| Mesh | [Accepted builder](mesh/OCTOBER26_CANONICALIZATION.md); `mesh.october26.build` accepts cell/boundary paths | Machine-local runtime lock; generic boundary preparation and dataset CLI needed. S10 `reproduce` is only a regression |
| GP initialization | [GP smooth/SVD](initialization/C3_GP_SVD.md); `gp_svd.fit` accepts K/nfit/seed, arbitrary genes/groups | Preparation/environment wrappers remain S10-specific |
| Quadrature | `sampler.registry_rule.load_registry_rule(path, expected_sha256=..., order=L)` derives tensor shapes from L | Existing L4/L14/L16 arrays verified exactly. Other orders need authenticated tables. Target still scientifically fixes ell_eta=.14 |
| GPU sampler | Periodic controllers, compact checkpoints, exact restart and original numerical kernels | S10 experiment wrapper embeds paths, K, L, type loops, split names and schedules; generic target/launcher needed |
| Prediction | `holdout_prediction` and `predictive_summary` implement conditional prediction/mixture score | Sidecar and geometry/split lookup are S10-specific; generic reporting needed |

## Reproduce the panel with the reusable selector

With dependencies installed and `src` on `PYTHONPATH`:

```text
python -m bsfm.preprocessing.gene_selection --animal-summary docs/recovery/gene-panel-20261104/EXPANDED_GP_ANIMAL_SUMMARY.csv --recipe config/preprocessing/johnston-gene-selection.json --output /external/path/selected-genes.json
```

Input is one CSV row per gene/celltype/animal, with `spatial_fraction` in [0,1]
or missing. Duplicate keys fail. The recipe supplies allowed types, threshold,
recurrence and optional expected animal count. Output includes every gene's
support/exclusion, source/recipe hashes and rationale. Existing output is never
overwritten. This selector does not fit GPs or reinterpret missing held-out scores.
Technical sections were aggregated by median upstream in the historical screen.

### Screening producer

`preprocessing.spatial_screen.screen_sample` supplies those upstream fits from
the existing dataset contract. Its recipe declares sample, ordered groups,
candidate genes, screening cells (`training_cells`) and numerical configuration.
`config/preprocessing/recovered-gp-screen.json` records the recovered settings;
its expression thresholds are explicitly in SCT units, not universal defaults.
The optional module CLI authenticates dataset and recipe hashes and records
package versions. `aggregate_animals` takes median spatial fractions across
technical sections and rejects duplicate blocks, conflicting identities and
unknown animals. It does not invent biological replication.

The fit was recovered by inspection from
`E:/johnston_brain/artifacts/GENE_REVIEW_20261004/review.py`, `fit_one`, lines
167–213, file SHA256
`8b590e72c4333a1241d5d3fca110cabc1b0cb43da7b5d3b8a8d96788b953173f`.
The Matérn-2.5 kernel, bounds, normalization, jitter, optimizer restart setting,
fixed per-group RandomState sampling and signal/(signal+noise) statistic are
preserved. The median aggregation is also visible in the already captured
`recovery/gene-panel-20261104/historical_gp_extension.py`. This bounded port
omits historical fitted-mean files, rendering, cache reuse and worker submission;
fit errors propagate instead of being hidden in sidecar error files. Expression
eligibility is explicit; it does not silently apply historical paper exceptions.

Two focused tests pass in the local Python environment with isolated
scikit-learn 1.4.2, joblib 1.4.2 and threadpoolctl 3.5.0: exact same-runtime
agreement with the inspected historical GP calculation on synthetic inputs,
fixed sampling, response-unit rejection, screening-population isolation,
technical-section aggregation and identity rejection. These are not a full
historical dataset reproduction or a justification for universal thresholds.

The original Johnston response recipe remains unchanged. Generic helpers are
not yet wired into its HDF5 production runner. `log_library_size` accepts raw
integer counts from the full measured gene universe before modeling selection;
caller supplies a target fixed independently or from training observations.
Integer checks cannot prove data provenance. Already-normalized responses enter
through an explicit imported-response contract, not through this transform again.
The Johnston natural-log SCT scale and axolotl library-normalized log2 scale are
different; no claim of interchangeability is made.

`center_from_training(response, cell_groups, training_mask)` fits means using
training cells only, applies those means to scoring cells, and fails if a group
has no training observations. It supports arbitrary group counts and names.

## Remaining implementation order

1. Dataset/response foundation implemented and checked on synthetic inputs and
   real axolotl import. Add a Johnston adapter/integration fixture; do not force
   identical normalization. See the dataset guide and validation receipt.
2. Screening GP producer and technical-section aggregation are ported with a
   bounded same-runtime test. Connect existing stage contracts without introducing
   a second preparation interface; replication policy remains explicit.
3. Expose mesh runtime/boundary configuration and connect generic GP initialization.
4. Generalize configuration at existing assembly/GPU launcher boundaries while
   preserving numerical kernels, saving and restart contracts. Validate on a
   second dataset before claiming generic execution.
5. Return to downstream scientific experiments separately after core integration.

Six focused tests pass: exact 91-gene recovery, same-type recurrence and duplicate
rejection, expression thresholds, library scaling/base, training-only centering,
and exact registry arrays for L4/L14/L16. These do not establish end-to-end axolotl
readiness, GPU performance or convergence. No new scientific run was launched.
