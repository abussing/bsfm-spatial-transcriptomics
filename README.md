# BSFM Spatial Transcriptomics

Clean, provenance-controlled development of the Bayesian spatial factor model
for spatial transcriptomics.

For continuation on another computer, start with the
[pipeline portability audit](docs/PORTABILITY_AUDIT.md) and
[current handoff](docs/CURRENT_HANDOFF.md). They distinguish committed code,
target-machine environments, passing tests and reproduced scientific outputs.

This repository contains recovered documentation, canonical raw-input preflight,
implemented, production-validated full-data SCTransform preprocessing, and the
accepted October 26 four-stage warp-mesh builder.
Historical implementations are
not authoritative and must not be copied or executed until their provenance,
purpose, and relationship to the intended method are understood.

## Current phase

Canonical full-data SCTransform v2 production passed for all 19 sections at
common correction depth 124. See the [production receipt](docs/preprocessing/audits/20261031_production_v2/README.md).
These artifacts are not eligible for primary holdout scoring; that requires
training-only preprocessing. Sampler Layers 1-3 and their architecture are
accepted; the complete sampler and production HPC workflow remain unimplemented.
Bounded Linux environment/test receipts are recorded separately. Canonical raw,
SCT-v2 bundles and S10 mesh are authenticated on the original Windows desktop;
transfer to laptop/HPC remains outstanding. See the
[desktop reconciliation](docs/environment/DESKTOP_RECONCILIATION_20261102.json). See the [preflight guide](docs/preprocessing/RAW_INPUT_PREFLIGHT.md)
for the CLI, dependencies, tests and artifact contract.

## Canonical mesh entry point

Use `bsfm.mesh.october26.build` with
[`config/mesh/october26-warp-basis.json`](config/mesh/october26-warp-basis.json).
The [canonical guide](docs/mesh/OCTOBER26_CANONICALIZATION.md) specifies the full
glial geometry population, required inherited far boundary, coordinate transform
and downstream interfaces. The module CLI is only an S10 historical regression;
there is no all-section mesh launcher. No all-section mesh run is claimed.

The mesh is a parsimonious latent-warp basis with outward grading and exact
inactive-vertex marginalization. S10's byte-identical reproduction is mechanical
regression evidence, not a scientifically optimal vertex count. The rejected
range-derived study has been removed from the active surface; its
[historical receipt](docs/mesh/REJECTED_PHASE0.md) points to Git history.

## Authoritative documents

The canonical cold-start initializer is `bsfm.initialization.gp_svd`; see the
[C3 GP-to-SVD guide](docs/initialization/C3_GP_SVD.md). S10 is accepted as
historically equivalent under the explicit cold-start regression criterion,
not byte-exact. It exports seeds only, leaves modeling Y unchanged, and requires
explicit K/nfit/seed arguments. No all-section initialization or sampler run is
claimed.

- `CAPABILITIES.md`: functionality the platform must ultimately provide.
- `AGENTS.md`: mandatory working rules for humans and coding agents.
- `docs/RECOVERY_PROCESS.md`: how historical implementations will be studied
  without assuming that the newest file is the best one.

