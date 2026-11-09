# BSFM Spatial Transcriptomics

A reusable workflow for Bayesian spatial factor modeling: input, normalization,
gene selection, mesh construction, initialization, GPU sampling and saved outputs.

- [Workflow guide](docs/WORKFLOW_GUIDE.md): methods, interfaces and known limitations.
- [Dataset contract](docs/preprocessing/DATASET_CONTRACT.md): import, response preparation and gene screening.
- [Current handoff](docs/CURRENT_HANDOFF.md): repository authority and environment/artifact navigation.
- [Working rules](AGENTS.md): preservation, provenance and execution requirements.

Reusable implementations live in `src/`; `config/` holds method settings, schemas
and fixed regression configurations. New dataset and run recipes live outside Git.
Tests and pinned scientific contracts establish the scope of each implementation.
Data, analysis reports, plots, logs and posterior outputs also stay outside Git.

The guidebook explains methods across datasets. It is not an analysis notebook or
a project diary. Historical recovery evidence is provenance, not another pipeline;
use the current interfaces linked above. The [provenance index](docs/recovery/README.md)
locates archived evidence without making it part of the new-dataset workflow.
