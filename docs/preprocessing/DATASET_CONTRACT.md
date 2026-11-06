# Portable dataset and response layer

This layer separates scientific response identity from the source file format and
model dimensions. It imports already-normalized, uncentered expression without
normalizing again. It prepares group-centered training and scoring arrays without
fitting a GP, constructing a mesh, or selecting a favorable gene panel.

## Dataset contract

`bsfm.preprocessing.dataset.write_dataset` accepts these exact NPZ arrays:

| Array | Shape | Meaning |
| --- | --- | --- |
| expression | genes x cells, float64 | Declared uncentered normalized response |
| coordinates | cells x 2, float64 | Source coordinates, with declared axes/units |
| gene_names | genes, Unicode | Unique exact identifiers; no alias rewriting |
| cell_names | cells, Unicode | Unique exact identifiers |
| group_names | cells, Unicode | Modeling group, not necessarily a cell type |
| sample_names | cells, Unicode | Sample/section membership |
| animal_names | cells, Unicode | Real biological identities, or empty when unknown |
| source_row_indices | cells, integer | Original row, unique within sample |

The metadata declares schema `bsfm.dataset.v1`, dataset ID, coordinate units,
whether animal identity is known, and normalization method, units, population and
evidence. Dataset identity does not imply that original transformation parameters
were learned independently of held-out cells. Missing animal identity is not
replaced with sample/group labels.

The writer publishes a fresh directory containing `dataset.npz` and `dataset.json`.
The manifest records the NPZ hash and original source hashes. The reader requires
an independently expected manifest SHA256, validates the payload hash, dimensions
and axes, and rejects duplicate or object-array members. No existing destination
is overwritten. The manifest preserves original source paths as provenance; it
does not require those paths to exist when reading a transferred bundle.

## RData adapter

`bsfm.preprocessing.import_rdata` reads an explicitly named list object and fields
using the repository's data-only R exporter. It does not source historical R code.
The current adapter accepts a dense numeric response, its exact dimnames, two
coordinate columns and a character group vector. Coordinate/group alignment is
an explicit source-layout assertion in the recipe; matching lengths alone cannot
prove biological alignment. No animal field is fabricated. Other layouts require
their own explicit adapters.

```text
python -m bsfm.preprocessing.import_rdata --source /external/source.RData --recipe config/datasets/YOUR_DATASET.json --rscript /path/to/Rscript --output /external/dataset
```

Supply machine paths via CLI. The recipe names source fields, their fingerprint,
alignment assumptions and verified normalization. Importing does not choose the
modeling population, genes, factor count or run length.

## Prepare a response using explicit names

A JSON selection has exactly `sample`, ordered `groups`, ordered `genes`,
`training_cells` and `heldout_cells`. Cells not in either list remain available
for the declared fixed-design geometry but do not enter fitting or scoring.
Splits must be disjoint and within the configured sample/groups. Each modeled
group must have training observations. Genes are looked up by exact identifier.

```text
python -m bsfm.preprocessing.dataset --dataset /external/dataset --manifest-sha256 EXPECTED_HASH --selection selection.json --output /external/path/prepared-response
```

Preparation normalizes coordinates by the selected sample/groups' coordinate
minimum and maximum axis span, using the fixed geometry population before
thinning/holdout. It estimates gene/group means on training cells only and applies
the same means to held-out responses. Group blocks follow the recipe order;
within each group cells follow increasing original source row. No gene variance
scaling occurs. Response receipts preserve the transform, means, source indices,
normalization declaration, manifest/selection hashes and output hashes.

`training.npz` and `scoring.npz` carry the existing model-input fields. The training
output passes the sampler's dimension/order contract for arbitrary groups and
genes. Geometry authentication, GPINIT fitting and run orchestration follow through
the interfaces in the [workflow guide](../WORKFLOW_GUIDE.md).

### Connect to the existing initializer

Add `--gpinit-contract` to the preparation command to emit `gpinit-input.json`
alongside the existing arrays. This uses the initializer's existing schema,
logical identity encoding and loader; there is no second preparation command
or new initialization algorithm. It requires the GPINIT Python dependencies.
For an ordinary fit, list all declared modeling cells in `training_cells` and
use `heldout_cells: []`; no experimental split is required.

```text
python -m bsfm.initialization.gp_svd --input /external/path/prepared-response/training.npz --contract /external/path/prepared-response/gpinit-input.json --output /external/path/gpinit --factors 12 --nfit 250 --seed 41
```

K=12, nfit=250 and seed=41 above illustrate CLI syntax, not recommended settings.
The exported contract preserves input byte and array hashes, normalization,
centering and coordinate-transform provenance. Preparation checks it with the
actual GPINIT loader before publishing the output directory. Preparation does
not fit GPs; the second command invokes the existing accepted initializer.

## Normalization and gene selection

Keep response transformation, expression eligibility and spatial selection as
separate recipe decisions. Verify normalization from source evidence; never infer
it from a field name or apply a second transformation to an imported response.
Library normalization uses the full measured gene universe before gene selection,
an explicit target sum and an explicit log base. SCT is a separate accepted method;
its thresholds are not interchangeable with library-normalized response units.

Screen within the declared modeling groups. Expression eligibility uses explicit
detection, level and nonconstancy thresholds in the declared response units.
Spatial GP screening estimates signal/(signal + noise) with a Matérn-2.5 kernel.
The recipe supplies kernel settings, fitting-cell cap, seed and screening cells.
The [recovered numerical recipe](../../config/preprocessing/recovered-gp-screen.json)
and [method provenance](../recovery/gene-panel-20261104/README.md) document the
accepted starting method; expression thresholds are not universal defaults.

```text
python -m bsfm.preprocessing.spatial_screen --dataset /external/dataset --manifest-sha256 EXPECTED_HASH --recipe screening.json --output /external/screen.json
python -m bsfm.preprocessing.gene_selection --sample-screen /external/screen.json --recipe selection.json --output /external/selected-genes.json
```

The single-sample mode makes no biological replication claim. When real animal
identities exist, `aggregate_animals` takes technical-section medians and the
selector's `--animal-summary` mode evaluates the recipe's recurrence criterion.
Do not invent animals from sample or group labels. Both selection modes reject
inconsistent identities and preserve selection rationale. Do not select genes
using favorable downstream model-comparison outcomes.

## Resumable screening

Add `--checkpoint-dir /external/batches --batch-size B --workers W` to the screen
command. Batching partitions genes only; groups, geometry and per-group RNG draws
remain identical. Choose B and W for the available resources.

Completed batches are atomically published and checksummed. Resume binds inputs,
recipe, source dependencies, runtime and batch size. It reuses complete batches;
only a complete collection produces the final screen. At interruption, at most W
unfinished batches may require recomputation. Remove a stale `.lock` only after
confirming that all previous workers have stopped. Changed inputs or software
require a new output directory.

## Expression support and spatial amplitude

Spatial fraction alone is insufficient: a weak absolute signal can have a high
fraction. Review each gene within each group using:

| Measure | Interpretation |
| --- | --- |
| Detection and zero fractions | Coverage within the modeled group |
| Mean and positive-expression median | Expression strength in declared response units |
| Spatial fraction | Modeled spatial share of signal-plus-noise variance |
| Fitted-mean q90 minus q10 | Absolute spatial amplitude in response units |
| Fit warnings | Parameters reaching bounds or other optimizer concerns |

The screen CLI accepts `--review-screen SCREEN.json --screen-sha256 HASH
--minimum-spatial-fraction THRESHOLD`, together with the dataset, manifest, recipe
and fresh output arguments above. It authenticates inputs, geometry, ordered rows
and original fitting cells. It conditions saved kernels with `optimizer=None`;
hyperparameters are not reoptimized. Amplitude describes the fitted mean over
screening cells, not held-out performance. Signal SD rescales the saved signal
variance with the original fitting-response SD and is a distinct measure.

Where authenticated source counts exist, inspect positive-count median, singleton
fraction among detections and fractions above explicit count levels. Verify exact
gene/cell/group alignment. Transformed expression is not raw count support, and
integer counts are not automatically UMIs. Spatially coherent expression confined
to a region can remain useful despite zeros elsewhere. Inspect maps and threshold
sensitivity; keep these measures separate rather than hiding tradeoffs in an
unexplained combined score. Freeze justified thresholds and the final panel in a
recipe; keep exploratory rankings and plots external.

## Validation boundaries

Tests cover dataset identity/tampering, centering and ordering, unchanged training
results after held-out perturbations, historical selection equivalence, batch
resume and saved-kernel mean reconstruction. See `tests/test_dataset_contract.py`,
`tests/test_dataset_preprocessing.py`, `tests/test_spatial_screen.py` and
`tests/test_screen_batches.py` for executable checks. Detailed dataset-specific
receipts are referenced by [the evidence index](DATASET_LAYER_VALIDATION.json).

Current limits are dense response storage, single-sample preparation, explicit
source adapters and source-declared normalization provenance. Whole-population
normalization is not silently relabeled training-only. See the workflow guide for
initializer and mesh environment limits.
