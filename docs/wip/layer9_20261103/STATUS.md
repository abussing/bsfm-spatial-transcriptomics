# NONCANONICAL Layer-9 shutdown snapshot

Status: **UNREVIEWED, INCOMPLETE, NOT ACCEPTED. Do not run on scientific data.**
Accepted main baseline: `9c584353e74043e323ca327ff1764f9d094980d5`.
Preservation branch: `wip/layer9-orchestration-20261103`.

The user interrupted implementation to prioritize shutdown preservation and
canonical-artifact transfer. No Layer-9 capability has passed acceptance.

Completed draft work: six new orchestration modules for initialization/adaptation,
genesis, transaction publication/projection repair, storage, authenticated NPZ-only
inputs and the accepted CPU environment. Three test/support files contain a
synthetic historical initialization comparison, exact-resume and interruption tests.
All accepted Layers 1-8, scientific settings and environments are unchanged.

Validation is unfinished. The initial exploratory 100-step warmup test was stopped
for bounded runtime after progress through 80/100 on its first factor. A second
20-step-per-factor test was stopped on user shutdown instruction after reporting
first-factor acceptance [0.88, 0.833] and divergences [1, 2]. No complete test result,
complete synthetic exercise, source-provenance audit, or full-suite pass is claimed.
The test files were still being expanded while that exploratory process was active;
its partial log cannot validate the complete preserved snapshot. Both test process
trees were terminated. No S10 transition or scientific run occurred.

Unfinished work: inspect the draft against LAYER9A_DESIGN.md, finish initialization
and warmup equivalence checks, independently review genesis and transaction recovery,
exercise all crash boundaries and committed non-replay, finish runtime identity and
spectral-chart restoration review, run every sampler/provenance and canonical mesh
test, and produce a reviewed implementation report/source map/validation receipt.
No package installation, environment modification, HPC job or Layer-9 acceptance.

`work.patch` is the complete addition diff of the nine source/test files plus this
status and the byte-identical partial review log. `inventory.csv` gives exact byte
counts and SHA-256 values for those files and the patch; it excludes itself to avoid
cryptographic self-reference. The WIP commit and Git tree authenticate the inventory.
The ignored original review log remains locally in artifacts/review/layer9.
