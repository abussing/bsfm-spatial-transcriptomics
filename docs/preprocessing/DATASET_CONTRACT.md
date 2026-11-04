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

## RData adapter and axolotl recipe

`bsfm.preprocessing.import_rdata` reads an explicitly named list object and fields
using the repository's data-only R exporter. It does not source historical R code.
The current adapter accepts a dense numeric response, its exact dimnames, two
coordinate columns and a character group vector. Coordinate/group alignment is
an explicit source-layout assertion in the recipe; matching lengths alone cannot
prove biological alignment. No animal field is fabricated. Other layouts require
their own explicit adapters.

```text
python -m bsfm.preprocessing.import_rdata --source E:/axolotl/artista_data.RData --recipe config/datasets/axolotl-artista.json --rscript "C:/Program Files/R/R-4.5.3/bin/Rscript.exe" --output /external/path/axolotl-dataset
```

Supply actual machine paths via CLI; these are not embedded in the adapter. The
axolotl recipe names fields, the source fingerprint and observed normalization.
Imported group labels are all six broad clusters, not a selected analysis group.
Importing does not select the modeling group, genes, holes, K or run length.

## Prepare a response using explicit names

A JSON selection has exactly `sample`, ordered `groups`, ordered `genes`,
`training_cells` and `heldout_cells`. Cells not in either list remain available
for the declared fixed-design geometry but do not enter fitting or scoring.
Splits must be disjoint and within the configured sample/groups. Each modeled
group must have training observations. Genes are looked up by exact identifier.

```text
python -m bsfm.preprocessing.dataset --dataset /external/path/axolotl-dataset --manifest-sha256 EXPECTED_HASH --selection selection.json --output /external/path/prepared-response
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
genes. Geometry authentication, GPINIT fitting and run orchestration are separate
subsequent layers; this command does not claim those are already integrated.

## Validation and boundaries

Four focused tests cover portable readback/tampering, missing animal identities,
duplicate cells, group/gene ordering, exact centering, unchanged training results
after perturbing held-out values, source immutability and invalid splits/groups.
The initial test invocation also attempted to import GPINIT's validator, but the
local environment lacks scikit-learn. The passing interface check uses the actual
sampler input validator; no GPINIT numerical execution is claimed.

Current limitations: dense response storage, single-sample model preparation,
source-specific adapters, and user-declared original normalization provenance.
Whole-sample imported normalization is not silently relabeled training-only.
