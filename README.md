# BSFM Spatial Transcriptomics

Scientific rationale and reusable implementations for the Bayesian spatial
factor model: input, normalization, gene selection, mesh, initialization,
GPU sampling and saved outputs. Dataset recipes supply identities and settings;
shared methods should not require dataset-specific rewrites.

## Start here

- [Workflow guide](docs/WORKFLOW_GUIDE.md): current method map, interfaces,
  rationale links and remaining integration gaps.
- [Current handoff](docs/CURRENT_HANDOFF.md): active work, branch status,
  artifact locations and operational continuation.
- [Working rules](AGENTS.md): preservation, provenance and execution requirements.

The consolidated baseline includes accepted sampler Layers 1?8, SCTransform
preprocessing, the October 26 mesh builder and GP/SVD initialization. Main also contains the tested reusable preparation, screening, initialization
contract and mesh-boundary interfaces. GPU orchestration and periodic
saving/restart remain on the separately identified review branch; they have
execution evidence but are not yet promoted to main.
A complete generic new-dataset run command remains unfinished.

Use the existing numerical implementations and their linked contracts. Historical
implementations are evidence, not alternative entry points. Large data, meshes,
environments and posterior outputs stay external with recorded identities.
Historical audits and scientific results retain their original validation scope;
consult the current guide and handoff rather than treating old status prose as
current instructions.
