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

