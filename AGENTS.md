# Repository working rules

1. This repository is the only future source of authoritative BSFM code and
   documentation.
2. Historical BSFM folders are untrusted evidence. Do not execute or copy a
   historical implementation merely because it is recent or plausibly named.
3. Do not describe a component as current, best, verified, or production-ready
   without documenting the kind of evidence supporting that statement.
4. Separate narrow mathematical or mechanical invariants from scientific and
   judgment-dependent decisions.
5. Recover design intent and implementation lineage before selecting among
   historical candidates.
6. Do not submit HPC jobs without a committed run specification and explicit
   user approval.
7. Never edit scientific source code only on the HPC. HPC runs must identify an
   exact Git commit and frozen configuration.
8. Keep raw data, transformed matrices, environments, checkpoints, posterior
   draws, and large logs outside Git. Track their schemas, locations, and hashes.
9. Make one conceptual change per commit when practical, with a plain-language
   explanation of why it was made.
10. Update repository documentation whenever a consequential decision changes.
11. Consolidate rather than redevelop: recover the best-supported working
    implementation, port it conservatively, and perform a bounded reproduction
    test. Open-ended scientific redesign requires explicit user approval.
12. The repository must explain and implement reusable workflows for new datasets.
    Put dataset paths, gene panels, group labels, K, quadrature order and run
    lengths in explicit recipes. Derive dimensions from authenticated inputs.
    Fixed mathematical choices require a linked rationale and scope.
13. Distinguish reusable methods, dataset recipes and historical regressions.
    Preserve verified recipes and checkpoint identities while generalizing.
    Never infer normalization solely from a field name or silently double-log
    an already transformed matrix. A regression-only CLI is not a pipeline.
14. Gene-selection code must accompany panel provenance and scientific rationale.
    Adaptation to new datasets must handle biological replication and response
    units explicitly. Do not select genes for favorable deep-versus-flat test
    outcomes. Record remaining workflow gaps in docs/WORKFLOW_GUIDE.md.

