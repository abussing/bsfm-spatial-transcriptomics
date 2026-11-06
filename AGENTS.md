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
6. HPC jobs require an explicit, frozen external run specification and user
   authorization. Pin the source Git commit and artifact hashes in that manifest;
   do not commit individual analysis specifications to this repository.
7. Never edit scientific source code only on the HPC. HPC runs must identify an
   exact Git commit and frozen configuration.
8. Keep raw data, transformed matrices, environments, checkpoints, posterior
   draws, and logs outside Git. Keep per-analysis paths and hashes in external
   manifests; Git owns reusable schemas and fixed method-validation evidence.
9. Make one conceptual change per commit when practical, with a plain-language
   explanation of why it was made.
10. Update repository documentation whenever a consequential decision changes.
11. Consolidate rather than redevelop: recover the best-supported working
    implementation, port it conservatively, and perform a bounded reproduction
    test. Open-ended scientific redesign requires explicit user approval.
12. The repository must explain and implement reusable workflows for new datasets.
    Put dataset paths, gene panels, group labels, K, quadrature order and run
    lengths in explicit external recipes. Derive dimensions from authenticated inputs.
    Fixed mathematical choices require a linked rationale and scope.
13. Distinguish reusable methods, dataset recipes and historical regressions.
    Preserve verified recipes and checkpoint identities while generalizing.
    Never infer normalization solely from a field name or silently double-log
    an already transformed matrix. A regression-only CLI is not a pipeline.
14. Gene-selection code must accompany panel provenance and scientific rationale.
    Adaptation to new datasets must handle biological replication and response
    units explicitly. Do not select genes for favorable deep-versus-flat test
    outcomes. Record remaining workflow gaps in docs/WORKFLOW_GUIDE.md.
15. Keep the guidebook dataset-independent: explain each reusable method once.
    Individual dataset imports, panels, run recipes, job scripts, rankings, plots,
    logs and receipts belong in external analysis directories, not Git. A new
    analysis must not require a repository change. Commit only reusable methods,
    interfaces, environment definitions, scientific rationale and focused tests.
    Synthetic examples and fixed evidence needed to validate a method are allowed;
    they must not grow into an analysis diary. Update guidance in place.
    Preserve historical scientific provenance and existing checkpoint identities.
