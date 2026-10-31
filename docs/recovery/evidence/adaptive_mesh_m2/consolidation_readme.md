# BSFM consolidation workspace

This directory is the non-destructive consolidation point for the 19-section
Bayesian spatial factor model as of 2026-10-30. It is deliberately **not** a
launchable production directory yet.

## Current status

- The four-stage fmesher geometry for all 19 sections has been visually
  approved by the user.
- The prepared fmesher package on the HPC contains 19 sections, 91 genes,
  20 factors, and a spatially balanced 50% sample within each cell type.
- Its final package certificate says `READY_FOR_CLOUD_GPU_PREFLIGHT`; no GPU
  smoke run was performed on that package.
- The older 20-factor/75%-cell HPC campaign uses the rejected old mesh and is
  not a source of restart checkpoints for the approved geometry.
- No new scientific run specification has been frozen.

## Contents

- `source_snapshot/`: read-only copy of the code and manifests embedded in the
  approved fmesher package. This contains historical launchers and is not the
  future clean launcher.
- `bsfm_cleanup_audit_20261030/`: inventories and hashes collected from the HPC.
- `CLEANUP_FINDINGS.md`: verified conflicts, authoritative assets, and material
  that must be quarantined.
- `RUN_SPEC_TO_DECIDE.md`: the decisions that must be made once, explicitly,
  before implementation or submission.
- `TARGET_LAYOUT.md`: proposed clean HPC layout and reliability requirements.

## Safety state

No HPC result directory has been deleted or moved. No old job has been
cancelled. No new MCMC job has been submitted.

