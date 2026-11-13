# Repository continuation

Read [AGENTS.md](../AGENTS.md) and the [workflow guide](WORKFLOW_GUIDE.md).
Inspect local Git status before updating a checkout; preserve local changes.
The workflow guide owns current interfaces and limitations. This file only points
to authority, environments and external evidence; do not append analysis progress.

## Authority

`main` contains the accepted numerical layers and reusable preparation, screening,
mesh, initialization, GPU runtime and periodic restart interfaces. Follow their
contracts rather than importing historical implementations.

`review/gpu-workflow-consolidation-20261103` contains additional experiment code
that has not been accepted wholesale. The older
`wip/layer9-orchestration-20261103` is historical evidence, not a branch to merge.
Promotion provenance is in [the existing validation record](recovery/REUSABLE_WORKFLOW_VALIDATION_20261104.json).

## Environments and artifacts

HPC: `abussing@login.rci.sc.edu`, SSH port `222`, interactive Duo. Never store
credentials. HPC submissions require a frozen external specification and explicit
authorization. Preserve immutable run checkouts and checkpoint identities.

Use [the external artifact index](external-artifacts.json) for the verified
canonical mirror and restoration references. Check its transfer receipt when
needed; do not repeat recovery because original Windows paths are unavailable.
The mirror's source inventory maps original paths to transferred payloads.

Runtime pins live in `environment/` and `config/sampler/hpc-gpu-runtime.json`.
Use validated platform-specific environments, not copied Windows environments.
The workflow guide's [new-HPC deployment boundary](WORKFLOW_GUIDE.md#moving-to-another-hpc)
records what is reusable and what still needs restoration or validation.

Dataset-specific evidence is located through
[the compact preprocessing index](preprocessing/DATASET_LAYER_VALIDATION.json).
Detailed receipts and analysis outputs remain external. Old run status is not
live status; query the relevant scheduler/output when continuing an experiment.
