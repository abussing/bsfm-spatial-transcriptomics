# BSFM Spatial Transcriptomics

Clean, provenance-controlled development of the Bayesian spatial factor model
for spatial transcriptomics.

This repository contains recovered documentation, canonical raw-input preflight,
and implemented, production-validated full-data SCTransform preprocessing.
Historical implementations are
not authoritative and must not be copied or executed until their provenance,
purpose, and relationship to the intended method are understood.

## Current phase

Canonical full-data SCTransform v2 production passed for all 19 sections at
common correction depth 124. See the [production receipt](docs/preprocessing/audits/20261031_production_v2/README.md).
These artifacts are not eligible for primary holdout scoring; that requires
training-only preprocessing. No BSFM model or HPC workflow has yet been frozen
in this repository. See the [preflight guide](docs/preprocessing/RAW_INPUT_PREFLIGHT.md)
for the CLI, dependencies, tests and artifact contract.

## Authoritative documents

- `CAPABILITIES.md`: functionality the platform must ultimately provide.
- `AGENTS.md`: mandatory working rules for humans and coding agents.
- `docs/RECOVERY_PROCESS.md`: how historical implementations will be studied
  without assuming that the newest file is the best one.

