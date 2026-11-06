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

## Validation and boundaries

Four focused tests cover portable readback/tampering, missing animal identities,
duplicate cells, group/gene ordering, exact centering, unchanged training results
after perturbing held-out values, source immutability and invalid splits/groups.
The original check used the sampler input validator. The subsequent generic
preparation-to-GPINIT integration test uses both real CLIs, all declared cells,
new group names, two factors and a small synthetic response. Exported arrays
match direct preparation exactly; saved seeds match direct initialization exactly;
changed identity hashes are rejected. All 14 initialization tests pass locally
with scikit-learn 1.4.2 installed in the isolated screening dependency directory.
This is bounded interface/numerical validation, not a new scientific-data fit.

Current limitations: dense response storage, single-sample model preparation,
source-specific adapters, and user-declared original normalization provenance.
Whole-sample imported normalization is not silently relabeled training-only.

## Reference adapter: axolotl provenance

Source file: `E:/axolotl/artista_data.RData`, 90,188,253 bytes, SHA256
`37287f741ddbd899ff7590143c8985d2d20588e6b32bab0879e93298c589c8cf`.
The user supplied Lulu Shang's Artista preprocessing example on 2026-11-04.
It identifies `data_use$count_use`, `cluster` and `location_coord` as the counts,
cell labels and coordinates. The [published tutorial](https://lulushang.org/Celina_Tutorial/Artista.html)
matches that workflow. It creates one-hot cell-type indicators, keeps types
representing more than 1% of observations, invokes preprocessing with threshold
5e-5, and then calculates kernels and tests genes. All six local broad groups
exceed 1% of the 4,410 cells. These groups are cell types, not animal IDs.

### Source inspection

Inspected [CELINA source revision 305f57958acace00811caea6bd9a92514249182c](https://github.com/shangll123/CELINA/blob/305f57958acace00811caea6bd9a92514249182c/R/CELINA.R):
`preprocess_input` obtains testing gene lists, calls `scater::normalizeCounts`
on the expression matrix, and subsets normalized rows afterward. The initial
5e-5 filter is applied to mean counts divided by each cell's library total, with
mitochondrial-name exclusion. Further cell-type lists use estimated relative
expression and abundance thresholds. This is not the BSFM recurrent spatial-GP
criterion. `Create_Celina_Object` also scales coordinates; its scaling should not
silently replace BSFM's separately declared geometry transform.

The pinned inspected source is not proof of the exact version originally used
to create the RData. The tutorial does not identify the original producer of
the saved `scater_norm` field. No CELINA model or tests were run in this recovery.

### Independently measured local representation

`count_use` and `scater_norm` contain matching ordered 16,586-gene and 4,410-cell
axes. `count_use` is nonnegative integer valued. The saved response reconstructs
as log2(1 + per-cell library-scaled counts), with a common scaled library total
approximately 10,397, to maximum absolute error 1.776357e-15. Its precise original
software execution history remains distinct from that numerical verification.

The [import recipe](../../config/datasets/axolotl-artista.json) reuses this response
without another logarithm, SCT fit or library-size correction. The
[dataset validation receipt](DATASET_LAYER_VALIDATION.json) records full payload
identity and independent sampled R/CSV readback. This imported whole-data
normalization is not relabeled training-only for future holdout evaluation.

### Workflow consequence

Keep three separate recipe decisions: response transformation, expression
eligibility, and spatial gene selection. CELINA's test-specific gene filters are
useful provenance, not an automatic replacement of the recovered BSFM rule.
Do not invent independent animals from cell types. The user has selected all six
supplied cell types and all 4,410 cells for the first axolotl analysis, with an
explicit within-sample spatial screen. No region restriction or holdout is used.

The [screen configuration](../../config/preprocessing/axolotl-gp-screen.json)
retains the recovered GP kernel, optimizer, seed, one thread and maximum 1,500
fitting cells per group. Eligibility requires detection in at least 30% of that
group, nonconstant expression and q90 >= 1 in the declared log2 response. Here
q90=1 means one library-scaled count; this is an explicit axolotl eligibility
choice, not a claim of equivalence with an SCT threshold. The saved response is
not transformed again. All 16,586 genes are evaluated for eligibility; 5,305
qualify in at least one type before any spatial fit. This is not a final panel.

The [selection recipe](../../config/preprocessing/axolotl-gene-selection.json)
retains genes with fitted signal/(signal+noise) >= 0.10 in at least one configured
type. The existing selector now accepts the existing GP-screen JSON directly:

```text
python -m bsfm.preprocessing.gene_selection --sample-screen /external/screen.json --recipe config/preprocessing/axolotl-gene-selection.json --output /external/selected-genes.json
```

This explicit single-sample mode reports no cross-animal recurrence assessment.
It rejects duplicate, mixed-sample and incomplete gene/group tables and records
each group's fit or exclusion status. It uses no held-out or model-comparison
score. The existing `--animal-summary` mode and Johnston recipe are unchanged.
A full screen must finish before its final panel is passed to preparation and
GPINIT; a timing pilot is not a gene-selection result.

### Resumable spatial screening

The existing screen CLI accepts `--checkpoint-dir /external/batches --batch-size 16
--workers 8`. These arguments split only the ordered gene list. Every batch uses
all configured groups, the same fixed geometry and the same per-group RNG draws.
The original `screen_sample` fitting function is unchanged. Worker count is an
execution choice, not part of the scientific sampling configuration.

Each completed batch is published atomically and checksummed. Resume binds the
dataset, recipe, source dependencies, numerical runtime and batch size; it reuses
completed batches without refitting. Only a complete batch collection produces
the final screening JSON. With eight workers, interruption can require repeating
up to eight unfinished batches. After forced termination, confirm the old job and
all workers have stopped before removing its stale `.lock` directory; never run
two writers against the same checkpoint directory. Completed output is reusable
only if its exact content agrees. Input, source or environment changes require a
new output directory.

The [existing validation receipt](DATASET_LAYER_VALIDATION.json) contains the
successful Linux pilot, exact input hashes and prepared full-run specification.
The full run records all genes' fit or exclusion results. Passing the 0.10 spatial
fraction gate does not automatically choose the final modeling panel: the user
will inspect the strongest within-cell-type signals before choosing that panel.

### Expression strength and spatial amplitude review

The spatial fraction gate is a candidate screen, not a final expression-quality
decision. Review each gene within each type using detection/zero fraction, mean
response, median positive response, and q90 minus q10 of its fitted spatial mean.
High fraction can coexist with weak expression or a small absolute spatial change.
Do not multiply these measures into an unexplained score, impose a universal
cutoff across response units, or discard a coherent region-specific gene solely
because it has zeros elsewhere. Inspect spatial maps alongside these summaries.

The existing screen CLI accepts `--review-screen SCREEN.json --screen-sha256 HASH
--minimum-spatial-fraction 0.1`, together with its existing dataset, manifest,
recipe and fresh output arguments. It verifies screen/input hashes, geometry,
ordered rows and original fitting-cell membership. Saved signal/noise/length
parameters are conditioned with `optimizer=None`; no GP hyperparameters are
reoptimized. Fitted-mean q10/q90 are calculated over screening cells, in original
response units. This is descriptive in-sample amplitude, not predictive validation.
Signal SD additionally rescales the saved standardized signal variance using the
original fitting-response SD; it is distinct from the fitted-mean amplitude.

Positive expression in a transformed matrix is not raw molecular support. When
source counts are available, join their exact gene/cell/type identities and inspect
positive-count median, singleton fraction among detections, and fractions above
explicit count levels. For axolotl the authenticated `count_use` matrix supports
this review, but counts are not asserted to be UMIs. The imported log2 response is
unchanged. No final panel, new hard expression cutoff, or fitted BSFM result is
implied by this review. Existing Johnston and axolotl screening recipes remain intact.
