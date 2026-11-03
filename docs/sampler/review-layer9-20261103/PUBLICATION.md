# Publication and HPC continuation

Published branch: `review/layer9-portability-20261103`, based on accepted main
`eeb6d9a903663907bbcb2d081bcec05475788ee1`. This preserves the locally reviewed
candidate; it does not promote Layer 9 to accepted main or authorize scientific
use. Original WIP `a87532ec30d6daacada3245e2cbeb105da4435ce` remains preserved.

The preceding README, validation receipt, patches and 45-entry inventory are a
frozen **pre-publication review snapshot**. Their statements about unstaged work
and no commits describe that checkpoint. This publication record supersedes
those operational-status statements; their numerical evidence is unchanged.
The inventory excludes itself; CSV line endings were normalized for Git during
publication. Its 45 listed file identities remain unchanged.

The user requested GitHub/HPC synchronization after reviewing the progress
summary and bounded Linux build proposal. Publish code and evidence on this
separate branch, mirror the exact Git commit to the HPC, and preserve all build
logs/receipts. No accepted scientific code or raw/prepared artifact is replaced.

The environment-only build specification is `LINUX_BUILD_RUN_PROPOSAL.json`.
It is limited to two CPUs, 8 GiB RAM, 30 minutes, no GPU, no scientific inputs,
and a fresh isolated prefix. Environment restoration is separate from numerical
Layer-9 Linux validation, S10 smoke and the training-only leave-out experiment.
Record the actual job ID/status and machine-readable report after submission;
this publication record alone is not evidence of an executed build.

HPC preservation roots:

- Existing canonical artifacts (unchanged):
  `/work/abussing/bsfm-consolidation/canonical-artifacts-20261103`.
- Exact source checkout: `/work/abussing/bsfm-consolidation/checkouts/<commit>`.
- Git bundle and synchronization receipt:
  `/work/abussing/bsfm-consolidation/reviews/layer9-portability-20261103`.
- Fresh proposed environment:
  `/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103`.

Do not treat full-data SCT as primary holdout preprocessing. Do not launch the
large section/hole grid. The missing downstream capabilities are listed in
`NEXT_RUN_READINESS.md`.
