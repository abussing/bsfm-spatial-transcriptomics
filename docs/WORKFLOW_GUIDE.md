# Reusable BSFM workflow: methods, recipes and current gaps

The repository is the scientific and operational reference for new datasets.
A method explains why and implements how; a recipe supplies dataset identities,
groups, units, populations and settings. Regression fixtures test preservation
of a recipe, rather than defining the only possible dataset.

This is the 2026-11-04 audit and first implementation increment. The complete
new-dataset workflow is **not yet available as one command**. Existing S10 runs
and exact source checkouts remain unchanged.

## Decision and implementation map

| Stage | Rationale / reusable implementation | Remaining coupling or gap |
| --- | --- | --- |
| Input | [Portable dataset contract](preprocessing/DATASET_CONTRACT.md), hash-pinned read/write and explicit RData adapter; real axolotl readback passes | Johnston raw adapter remains separate; more source formats require adapters |
| SCT | [Accepted design](decisions/SCTRANSFORM_DESIGN.md); `preprocessing/sct_core.R` accepts counts/depth | Extraction, depth policy and 300-gene validators are Johnston-specific; training-only SCT application unfinished |
| Library normalization | `preprocessing.normalization.log_library_size` takes explicit target sum and log base; distinct from SCT | Dense helper only; generic file ingestion and transform manifest needed |
| Existing response | Portable dataset manifest declares method/units/population/evidence; no automatic transformation | Original fit-population independence must be established separately |
| Expression eligibility | `preprocessing.gene_selection.expression_eligible`: explicit detection, level and nonconstancy thresholds | Thresholds depend on response units; screening GP producer and biological aggregation need a unified interface |
| Spatial selection | [Recovered rule](recovery/gene-panel-20261104/README.md); `select_spatial_genes` and CLI reproduce all 91 genes | Single-group axolotl cannot silently satisfy two-animal recurrence |
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
2. Recover/port screening GP producer and technical-section aggregation; connect
   expression eligibility and recurrent gene selection. Explicitly adapt the
   replication requirement for a single axolotl group.
3. Expose mesh runtime/boundary configuration and connect generic GP initialization.
4. Replace S10-only assembly, GPU launcher, saving/scoring and status lookup with
   a recipe-driven run command. Validate chronology and restart on a second dataset.
5. Complete a small axolotl deep/flat holdout with declared group, panel-selection
   population, response, mesh, K/L, schedule and scoring policy.

Six focused tests pass: exact 91-gene recovery, same-type recurrence and duplicate
rejection, expression thresholds, library scaling/base, training-only centering,
and exact registry arrays for L4/L14/L16. These do not establish end-to-end axolotl
readiness, GPU performance or convergence. No new scientific run was launched.
