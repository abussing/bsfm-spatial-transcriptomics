# BSFM pipeline portability audit

Audit date: 2026-11-02. Scientific/code baseline: `main` at
`49f33c441e1cde9e1b8139ffef0103993eaa0222`. Continuation work is on
`portability/hpc-continuation`, [PR #1](https://github.com/abussing/bsfm-spatial-transcriptomics/pull/1),
not yet an assertion that those changes are merged into main.

The new Windows computer has the Git checkout and authenticated Git/HPC access.
The new execution target inspected here is Linux HPC. No scientific runtime or
canonical output reproduction on this Windows computer is claimed. The former
Windows machine's accepted receipts remain evidence of its completed work.

## Four separate readiness levels

1. **Code:** canonical implementation, decisions, configurations and contracts
   are committed. Historical code on HPC is reference evidence only.
2. **Environment:** the required runtime and dependencies are installed in an
   isolated target environment. Source downloads alone do not meet this level.
3. **Tests:** identified checks passed in that target environment, with a receipt.
   Old-machine test results are not new Linux results.
4. **Outputs:** a named canonical scientific artifact was reproduced and compared
   under its accepted criterion. Environment tests and synthetic sampler tests do
   not establish this level, nor do they establish posterior convergence.

## Readiness by capability

| Capability | Canonical code in Git | Environment on Linux HPC | Tests on Linux HPC | Canonical outputs reproduced on Linux HPC |
| --- | --- | --- | --- | --- |
| Raw-input preflight | Yes: `bsfm.preprocessing.raw_preflight` and frozen section/panel contracts | Canonical preprocessing Python environment not restored/validated | Not rerun here | No new full-cell audit; former machine accepted 432,794 cells and depth 124 |
| SCTransform and modeling responses | Yes: SCT core, validators, single-section and sequential 19-section runners | Full SCT R/Bioconductor and Python dependencies remain to restore | Not rerun here | No; accepted all-19 v2 receipts are in Git, but their response bundles are not located on accessible storage |
| Mesh R runtime | Source/version locks and isolated Linux builder present on continuation branch | Job **22012386 failed** during optional R NEWS.pdf generation; no runtime/package installation completed | Syntax/CLI/allocation guard passed; fresh R package checks not reached | Not applicable to environment build; it did not construct a mesh |
| Canonical October-26 mesh | Yes: `bsfm.mesh.october26.build`, R builder and frozen settings | R job above addresses only the R side; canonical Python mesh environment still needs Linux restoration | No new canonical mesh/R test suite run | No; source geometry and topology references recovered, but the full preview projector/certificate and canonical sampler-facing export remain unresolved |
| GP-smooth SVD initialization | Yes: `bsfm.initialization.gp_svd` | Its separate pinned Python/scikit-learn environment is not restored/validated here | The recorded 13 tests belong to the previous machine; no new Linux initializer tests | No; historical S10 observations/seed/certificate are authenticated and available for a future bounded comparison |
| Sampler Layers 1–3 | Yes: small canonical Gaussian/PX, spectral/active-marginalization and frozen finite-feature/direct-W modules | Separate CPU/x64 Python 3.11.14 environment installed; seven numerical package pins match | **75 passed**, zero skips, job **22012334**; seven exact same-environment historical/port comparisons | Synthetic mechanical equivalence only; no new full-cell S10 smoke, posterior fit or scientific output |
| Complete Gibbs sampler and production execution | Not complete: centered fixed-W target, joint-eta PCG, NUTS/adaptation, complete sweep, restart, diagnostics and launchers remain | No canonical GPU/production environment | No complete-sampler tests or run | None; historical HPC campaigns do not establish a completed canonical implementation |
| Posterior plots/covariances, sender integration, Wasserstein, matched covariance sampling and spatial-hole prediction | Requirements/recovery context in CAPABILITIES.md; no complete canonical implementations established | Not established | Not established | Not established; training-only holdout preprocessing also remains pending |

Sampler evidence: [passing audit](environment/HPC_SAME_ENVIRONMENT_VALIDATION.md),
[machine-readable result](environment/HPC_SAME_ENVIRONMENT_22012334.json).
The first Linux run failed its Windows-fixture gate and remains preserved.
The passing audit uses independently evaluated, hash-authenticated original
functions in the same Linux runtime. Original fixture bytes and numerical
tolerances are unchanged. It does not claim Windows/Linux bit equality.

Previous-machine evidence: [preprocessing production](preprocessing/audits/20261031_production_v2/README.md),
[mesh canonicalization](mesh/OCTOBER26_CANONICALIZATION.md),
[initializer acceptance](initialization/C3_GP_SVD.md),
[sampler Layer 3](sampler/LAYER3.md). These accepted results are not lost or undone
by the uncompleted Linux restoration.

## External artifacts: available versus unresolved

The [external-artifact manifest](external-artifacts.json) is the per-file/path
inventory; [recovery status](environment/HPC_RECOVERY_STATUS.md) records search
coverage. Do not infer absence from an unavailable old drive or a bounded search.

| Dependency | Current evidence | How to close the gap |
| --- | --- | --- |
| Historical 19-section modeling inputs | All 19 files hash-match the preparation contract; 300 genes and 187,100 glial cells, including raw subsets and identity metadata | Already available on HPC; use their recorded hashes and retain historical labeling |
| Full-cell raw input | Accepted H5AD identity: 5,483,600,151 bytes, SHA-256 `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`; matching accessible copy not located | Trace existing storage/transfers first. Verify a recovered copy against the identity. Glial subsets cannot replace the all-cell SCT fitting population. Public retrieval is a fallback, not an established requirement |
| Canonical all-19 response bundles | Production manifests and validators are in Git; payloads not located | Recover and validate the six-file bundles against committed manifests, or regenerate only after authenticated raw input and validated SCT environment are available |
| S10 mesh construction inputs | Five source-geometry files restored exactly from HPC SOURCE_INPUTS.zip | Available under `/work/abussing/bsfm-consolidation/recovered/s10-source-geometry-20261102`; no new adapter needed |
| S10 historical preview | Vertices and triangles restored from byte-identical prepared copies | Locate full-cell `A_proj.mtx` and `CERTIFICATE.json`, or explicitly design a bounded comparison route; do not fabricate reference files or substitute the thinned projector |
| Canonical S10 sampler-facing export | Expected hash in manifest; payload not located | Recover and authenticate it or regenerate after mesh environment/input gates; previous full-cell sampler smoke is not rerun until its geometry is available |
| Historical sampler/GP references and L16 rule | Selected HPC files authenticated; canonical frozen L16 arrays and synthetic sampler fixtures already in Git | Available for bounded reference checks; no raw-data download is needed for sampler unit tests |
| Linux R build inputs | R source and 33 mesh sources authenticated; matching UDUNITS C headers separately authenticated | Retain failed job 22012386; review a narrowly corrected fresh build specification before retrying |

## Environment restoration routes and limits

- **Sampler CPU:** [setup and restoration](environment/HPC_CPU_SETUP.md) plus
  [Linux wheel lock](../environment/sampler-linux-cpu/requirements.lock.txt).
  The venv shares the historical base Python runtime. The retained ml_dtypes
  wheel is authenticated; complete compiler/sysroot/source-build reproducibility
  is not established. Preserve the base runtime and wheel cache.
- **Mesh R:** [Linux builder](../environment/mesh-linux/README.md) and unchanged
  [approved specification](environment/HPC_R_MESH_BUILD_RUN.json). Existing conda
  compilers/system libraries are external read-only dependencies. A successful
  build establishes versioned runtime validation, not standalone or byte-exact
  environment restoration, and not mesh-output reproducibility.
- **Mesh Python:** use [accepted mesh locks](../environment/mesh/README.md) to
  prepare a separate Linux installation with platform-specific artifacts. The
  sampler Python environment is not a substitute for this different lock.
- **SCTransform:** [environment specification and source locks](../environment/sctransform/README.md)
  cover the full R/Bioconductor stack. The 33-package mesh build does not restore
  it. Linux restoration/validation and preprocessing Python dependencies remain.
- **GP initialization:** [separate environment](../environment/gpinit/README.md)
  pins scikit-learn 1.4.2 and its numerical dependencies. Restore and test it
  separately; numerical cold-start equivalence is the accepted historical
  criterion, with exact same-environment determinism/readback still required.

## Permissions and sequence

The approval covered **job 22012386**, which ran using the committed build
specification unchanged and a fresh isolated output prefix. It failed in optional
documentation generation after 3 minutes 22 seconds. The [execution receipt](environment/HPC_R_MESH_BUILD_22012386.json),
logs and [machine-readable package/version report](environment/HPC_R_PACKAGE_VALIDATION_22012386.json)
are retained; all 33 package installations and fresh-session checks were not
reached. A changed retry requires a new committed specification and approval.
That approval does not include real-data mesh
construction, SCTransform fitting, model fitting, GPU execution or another
sampler layer as part of this portability task.

Read-only inventories, hash checks, source acquisition and repository
documentation can proceed. Under [AGENTS.md rule 6](../AGENTS.md), additional HPC
jobs require a committed run specification and explicit approval. Changes to
settled science or dependency versions also require the applicable explicit
decision; routine path restoration must not silently change either.

Immediate order: review/approve the minimal R build correction, preserving the
failed receipt and original specification. The [prepared retry specification](environment/HPC_R_MESH_BUILD_RETRY_RUN.json)
changes only optional PDF generation and retains the same resource limits; it
has not been submitted. Then close mesh Python/reference gaps; restore the separate initializer
and SCT dependencies as bounded tasks; recover or regenerate canonical payloads
under their validation contracts. Missing raw data does not block bounded future
sampler ports. Completing those ports is implementation work, not an environment
restoration claim. K, chain counts, run lengths and save cadence remain undecided.

On another computer, start here and in [CURRENT_HANDOFF.md](CURRENT_HANDOFF.md),
then follow the linked inventory and exact receipts. Update this table when a
gate changes; retain failed evidence and keep environment/test/output claims
separate. No complete end-to-end runnable canonical pipeline is claimed today.
