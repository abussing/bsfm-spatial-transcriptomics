# Canonical SCTransform environment decision

Decision date: 2026-10-30. Authority: explicit user approval following the
[feasibility report](../environment/SCTRANSFORM_ENVIRONMENT_FEASIBILITY.md).
Baseline: `c88fdefd746887f0cca818b794ccfbce5035c9aa`.
Status: **environment specification frozen; local build and bounded synthetic/S00
validation completed under the 2026-10-31 authorization and accepted**.
The original approval boundaries below describe this 2026-10-30 decision.
The later assignment authorized materialization and bounded validation before
commit; see the [build evidence](../environment/SCTRANSFORM_ENVIRONMENT_BUILD.md).
It did not authorize the other 18 sections, HPC execution or a version change.

## Frozen environment and deliberate amendment

| Component | Frozen version |
| --- | --- |
| R | 4.5.3 |
| Bioconductor | 3.22 |
| Seurat | 5.4.0 |
| SeuratObject | 5.4.0 |
| sctransform | 0.4.3 |
| Matrix | 1.7-4 |
| glmGamPoi | 1.22.0 |

This explicitly amends the historical glmGamPoi 1.25.1 development target to
released glmGamPoi 1.22.0. It is **not an exact historical reconstruction**.
The purpose is uniform regeneration of all 19 sections under the
[scientific response contract](SCTRANSFORM_DESIGN.md), not byte reproduction of
the mixed historical outputs. No numerical equivalence between glmGamPoi
versions has been established. The version change requires the validation
below; release status alone does not prove the desired behavior.

Bioconductor 3.22 is officially paired with R 4.5 and supports 64-bit Windows
and Linux. Its release announcement also notes Windows binary-builder
limitations, so binary availability must be verified during acquisition.
[Official release announcement](https://new.bioconductor.org/news/bioc_3_22_release/).

The historical 1.25.1 source is not lost: an immutable candidate commit was
found, but no recovered record attests that the historical run used it. The
amendment is an explicit choice of a released dependency stack, not a claim
that 1.25.1 is unavailable or wrong. Historical evidence remains unchanged.

The [machine-readable specification](../../environment/sctransform/environment-spec.json)
separates frozen versions, verified Git identities and metadata checksums from
archive SHA-256 values still requiring approved acquisition. It is not a
completed source lock or a substitute for a generated `renv.lock`.
The complete transitive dependency set, renv/BiocManager versions, Windows
distribution identity and compiler/toolchain are still to be resolved and
locked. No floating dependency or binary substitution may be hidden in a build.

## Execution and reproducibility strategy

1. Initial authoritative normalization will use a local, user-owned Windows
   x86-64 environment outside this repository. The authenticated H5AD is
   mounted locally. Do not replace the existing system R or use its shared
   package library. Select the new executable explicitly and verify library
   isolation before loading packages.
2. Use a real `renv.lock`, produced from the resolved and validated environment,
   together with a source lock containing exact URLs, commits where applicable,
   and measured SHA-256 hashes for every acquired artifact and dependency.
   Record both source and binary identities if Windows binaries are used;
   source metadata must not be presented as a hash of a binary.
3. Preserve the absolute executable, exact commands, Git commit, configuration,
   input identity, session/package descriptions, OS, compiler, BLAS/LAPACK,
   RNG and thread settings, warnings, exit codes and validation results.
   The full-data depth remains 124 for the accepted source population; it is
   not automatically the training-only holdout depth.
4. After the source-locked local environment works, add a Linux container
   definition for independent verification. Pin its base image and all build
   inputs; record the built image digest and validation results. Cross-platform
   numerical agreement must be assessed separately from repeatability within
   one frozen environment. Any tolerance must be specified before that check,
   with differences reported rather than silently accepted.
5. The current HPC Singularity 2.3.1 runtime is not on the initial execution
   path. Modern image compatibility and site permissions remain unverified.
   No HPC normalization job, runtime upgrade or container execution is approved.

renv captures package state but not all OS, compiler or BLAS/LAPACK effects.
The local command/session/source records are therefore required now; a future
container adds independent verification rather than certifying results merely
by existing. [Official renv container guidance](https://rstudio.github.io/renv/articles/docker.html).

## Required future validation

These are acceptance requirements, not tests already executed. Validation
must fail clearly on an unmet invariant; it must not switch methods, remove
cells/genes or loosen checks to pass.

| Check | Required evidence |
| --- | --- |
| Environment identity | Exact frozen versions, Bioconductor 3.22 dependency provenance, isolated library paths, complete source/binary hashes and session/build records. No unrecorded updates or development dependency drift. |
| Effective fit method | Explicit SCT v2 and an asserted effective `glmGamPoi_offset` method from the actual dispatch/model records. Missing glmGamPoi or fallback is a failure. |
| Fitting population | All requested eligible cells actually used for parameter estimation. Record requested and realized ordered cell identities/counts; `ncells=N` alone is insufficient proof. Use the full 300-gene input before the modeling subset and record gene-estimation eligibility. |
| Repeated synthetic fits | At least two fresh R sessions with identical synthetic counts, order, configuration, explicit seed/RNG and thread settings. Require exact numerical equality of fitted numerical parameters and corrected/data matrices within that frozen environment; compare semantic content, not timestamp-bearing object serialization. |
| Response extraction | Verify exactly, with zero numerical tolerance and aligned axes, that final `SCT/data = log1p(SCT/counts)`. Record maximum absolute difference as zero. No second log1p or variance scaling. Residual `scale.data` does not define this response. |
| Common-depth correction | Call `sctransform::correct_counts` with an explicit common depth, repeat with the same raw input/model, and require identical finite nonnegative integer corrected counts. Exercise an unequal-depth synthetic fixture with a common-depth rule computed independently of the implementation; do not rescale already corrected/logged matrices. |
| Audit recording | Record package/source/session identities, fitting/correction parameters, seeds, actual fitting cells, gene availability, output axes/hashes, warnings and all assertions. A configured option is not execution evidence. |
| S00 smoke | After synthetic validation and separate run approval, run only `S00__Trem2_5xFAD4`, with all 20,719 eligible cells and all 300 genes from the accepted raw fingerprint. Use full-data depth 124, apply the response/handoff checks, and retain model and output identities externally. Record resource limits in a committed run specification first. |
| Release to all sections | Review the bounded S00 result before approving the full 19-section run. This decision does not authorize either run. |

Any failure of deterministic fitting or exact layer equality is a finding to
resolve explicitly, not permission to weaken the contract. The seed/RNG,
thread count, synthetic fixture and S00 resource limits must be frozen in the
future validation/run specification. This checkpoint adds no validation code.

## Artifact and approval boundaries

Future Git content: environment/run decisions, container definition after local
validation, `renv.lock` and its activation/settings files, immutable source lock,
validation code, small aggregate validation records, and external-artifact
manifests. Package archives, installed libraries, environments, containers,
expression/model objects and large logs stay outside Git with locations/hashes.

Next is a separately approved acquisition/build step: obtain the exact R
distribution and package sources, measure archive SHA-256 values, resolve the
complete dependency graph and toolchain, generate the real lockfile, then run
the authorized synthetic validation. No download, installation, build, SCT
implementation, real-section smoke or all-section run occurs in this commit.
