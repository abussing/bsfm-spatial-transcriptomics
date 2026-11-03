# Current BSFM handoff

## Latest execution checkpoint: small L4 smoke completed

Job **22013500** completed successfully in **2 minutes 32 seconds**, exit 0:0,
from review commit `9823423a1315070b50c01a18f711d424f2b2b691`.
The user requested a lower-L, small execution check after the L16 attempt hit
its wall-time cap. This run used **24 cells, two factors, L4/64 features,
20 warmup steps per factor and two sweeps total**.

Both factors completed adaptation; sweep 1 was saved, a fresh process restored
the run and completed sweep 2, and a third process verified completed non-replay.
There were four warmup divergences and zero sweep divergences. Convergence was
not assessed. This validates the bounded L4 execution/restart path, not L16
scientific performance, full-cell fitting or held-out prediction.

The original L16 job 22013422 timed out before saved genesis; its preflight
checks passed and its incomplete attempt remains preserved. Slurm denied the
requested live wall-time extension. The successful retry used 30 minutes of
headroom without increasing iteration counts.

The retry derives joint-eta feature dimensions from the authenticated rule
instead of two fixed 1,024-column checks. Same-runtime L16 comparisons against
the previous implementation passed exactly for draws, diagnostics, audit and
RNG on both local Windows and HPC. This boundary-only change is on the review
branch; accepted main's scientific code and canonical L16 registry are unchanged.
The frozen 181-unchanged-files receipt describes the earlier candidate, not
this subsequent user-authorized boundary change.

Read the [completion report and receipts](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/review/layer9-portability-20261103/docs/sampler/s10-subset-smoke-20261103/RESULTS.md).
External outputs:
`/work/abussing/bsfm-consolidation/evidence/s10-subset-smoke-22013500`.

No leave-out fit has been submitted. The next development task is the single
deterministic chunk workflow: training-only preprocessing/initialization,
fixed mesh, warped and matched flat fits, and omitted-cell prediction/scoring.
Do not repeat completed artifact recovery or lower-L smoke merely to regain
context. Layer-9 code remains on the review branch, not merged into main.
Full L16 execution/performance and scientific-run settings remain separate
unverified requirements before claiming a production holdout result.

## Current continuation: Linux checks and small S10 proposal

The review branch `review/layer9-portability-20261103` now preserves the Linux
results and a user-requested small S10 execution proposal. Read
[the current review report](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/review/layer9-portability-20261103/docs/sampler/linux-review-20261103/REVIEW_RESULTS.md)
and [the small smoke specification](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/review/layer9-portability-20261103/docs/sampler/s10-subset-smoke-20261103/RUN_SPEC.json).
These supersede older pending-Linux operational statements below.

- Job 22013414 at a496b7c: 46 focused Layer-9 tests passed. The ordinary
  195-test suite recorded 27 saved-reference failure entries and one chart
  rounding-plateau test error. Mesh checks: seven passed, two R-dependent
  checks skipped, one import error due to missing psutil. Overall job FAILED,
  exit 1:0; all stages completed. This is not a full regression-suite pass.
- Job 22013415 at 5260e1c: 75 Layers 1-3 audit tests passed; independent
  historical/port comparisons for Layers 5 and 6 matched exactly on HPC.
- Job 22013417 at 8abee70: all ten final storage tests passed, including the
  normalized ownership guard added after job 22013414 began.
- All 181 accepted source/test/config/environment/schema blobs checked against
  the shutdown baseline remain unchanged. No scientific Layer-9 merge occurred.
- Small S10 derivative smoke job 22013422 was submitted from clean review
  commit 1aecadb6a95810d2182b3944694a5a9ae7b08854. Its status must be checked;
  submission is not a pass. No leave-out scientific fit has been submitted.

The next proposal uses only 24 cells, two sliced GPINIT factors, 20 warmup steps
per factor (the supported minimum), and two sweeps with a fresh-process restart,
under a ten-minute cap. It first gates on same-runtime Layer-4 comparisons and
an exact chart-boundary probe. Full-data SCT/GPINIT remain ineligible for primary
holdout scoring; the subset is a labeled execution derivative, not new canonical
preparation or a full-cell validation. No mesh or GPINIT regeneration is proposed.

## Continuation on the replacement computer: 2026-11-03

Accepted scientific capabilities remain Layers 1-8. The corrected Layer-9
candidate and its review evidence are published separately on
[`review/layer9-portability-20261103`](https://github.com/abussing/bsfm-spatial-transcriptomics/tree/review/layer9-portability-20261103).
This documentation update does not accept or merge that implementation.
Read the [publication record](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/deaaf833d9d77bf4db594d3efcfe0ca217392f12/docs/sampler/review-layer9-20261103/PUBLICATION.md),
[implementation review](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/deaaf833d9d77bf4db594d3efcfe0ca217392f12/docs/sampler/review-layer9-20261103/IMPLEMENTATION_REVIEW.md),
and [validation receipt](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/deaaf833d9d77bf4db594d3efcfe0ca217392f12/docs/sampler/review-layer9-20261103/VALIDATION.json).
The original WIP below remains historical evidence; resume from this newer
review branch without overwriting preserved local work.

Windows review evidence: 36 expanded Layer-9 tests passed. A later saved-modal
domain guard passed five focused tests and exact retained-genesis restoration;
five synthetic runtime-input checks also passed. The ordinary accepted-layer
suite ran 195 tests with eight saved-fixture failures. Separate authenticated
same-environment original/port comparisons passed for Layers 1-3, 5 and 6;
these do not erase the saved-fixture failures. Mesh checks: seven passed, one
R-dependent test skipped. Accepted Layers 1-8 files were checked unchanged.

Git source and external review evidence are mirrored at:

```text
/work/abussing/bsfm-consolidation/reviews/layer9-portability-20261103
/work/abussing/bsfm-consolidation/checkouts/460ccdd6ca523d22f2c61c0cbacdf0f1f82ba0de
```

The original review transfer verified 80 external evidence files and 45 review
inventory entries, with its receipt committed on the review branch. Subsequent
environment-build corrections were transferred as SHA-256-verified Git bundles
and checked out at their exact commits. Canonical artifact recovery was not
repeated; the 187-file mirror below is unchanged.

The authorized isolated Python environment build is separate from numerical
validation. Job 22013403 failed before installation because the selected
ml_dtypes wheel required newer glibc; job 22013404 failed before compilation
because the system CMake module could not start on the compute node. Logs and
receipts are preserved. Job 22013405 identified an unloaded compiler library;
job 22013406 compiled successfully but its wheel-version guard rejected metadata
from an incompatible build backend. Job 22013408 uses commit
`460ccdd6ca523d22f2c61c0cbacdf0f1f82ba0de`, compiles the same ml_dtypes 0.6.0 from
authenticated source, and isolates compatible build tools. All 13 runtime
package versions remain unchanged; limits are 2 CPUs, 8 GiB and 30 minutes.
See the [run specification](https://github.com/abussing/bsfm-spatial-transcriptomics/blob/460ccdd6ca523d22f2c61c0cbacdf0f1f82ba0de/docs/environment/layer9-linux-20261103/RUN_SPEC.json).
Job 22013408 completed with exit 0:0 in 74 seconds, batch MaxRSS 803116K.
All 13 runtime versions, dependency checks, CPU/x64 and module-path isolation
passed. Its successful installation is:

```text
/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
```

The build used `module load gcc/12.2.0 mpfr/4.1.0`; preserve that context until
runtime shared-library requirements are validated. The [environment history and receipts](https://github.com/abussing/bsfm-spatial-transcriptomics/tree/a2bb204545717257b4f440ffa185626527925178/docs/environment/layer9-linux-20261103)
record the source build, exact versions and separate failed attempts. This
establishes environment restoration only, not Linux sampler validation.

Next: finish Linux runtime portability and Layer-9 validation/review, then a
separately specified S10 mechanical integration smoke. Training-only holdout
preprocessing, the matched identity-warp control and prediction/scoring remain
outstanding. No S10 fit or leave-out job has been submitted by this continuation.

The sections below preserve the original accepted shutdown checkpoint.

Updated 2026-11-03 after completed shutdown preservation and artifact transfer.
This supersedes the earlier handoff's pending-transfer statements; older audits
remain evidence of their original inspections.

## Accepted baseline and unreviewed work

Accepted scientific/preparation main baseline:
`9c584353e74043e323ca327ff1764f9d094980d5`
(`docs: register canonical S10 full-cell preparation artifacts`). The subsequent
main commit containing this handoff changes documentation only.

Read [AGENTS.md](../AGENTS.md), [CAPABILITIES.md](../CAPABILITIES.md), the
[sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md),
[Layer 8](sampler/LAYER8.md), [Layer 9A design](sampler/LAYER9A_DESIGN.md), and
[accepted S10 full-cell preparation](initialization/S10_FULLCELL_PREPARATION.md).
Layers 1-8 are accepted. Layer 9 and leave-out prediction are **not accepted**.
The Layer-9A design's original preparation gaps are resolved only to the extent
established by the separate accepted S10 v2 receipt; it is not implementation
validation.

The interrupted Layer-9 draft is preserved separately on GitHub:

- Branch: `wip/layer9-orchestration-20261103`.
- Commit: `a87532ec30d6daacada3245e2cbeb105da4435ce`.
- Status: **UNREVIEWED, INCOMPLETE, NONCANONICAL. Do not run on scientific data.**
- Thirteen committed files: six draft source modules, three test/support files,
  and `docs/wip/layer9_20261103/{STATUS.md,focused-partial.log,inventory.csv,work.patch}`.
- The inventory authenticates twelve files, excluding itself to avoid circularity;
  all twelve byte counts/hashes were verified against the pushed Git blobs.
- No complete Layer-9 test pass or synthetic continuation result exists. Both
  exploratory test process trees were stopped. The retained partial log predates
  the final snapshot of tests and does not validate that snapshot.
- All accepted Layers 1-8 numerical code, fixtures and environments remain unchanged.

The draft includes initialization/adaptation, genesis, transaction publication
and repair, storage, and authenticated NPZ-only inputs. Review it against the
approved design before further development. Do not merge it as accepted code.

## Canonical artifacts: verified HPC computational mirror

HPC: `abussing@login.rci.sc.edu`, SSH port `222`, interactive authentication/Duo.
Destination:

```text
/work/abussing/bsfm-consolidation/canonical-artifacts-20261103
```

**Complete and independently verified at 2026-11-03 06:40:32 UTC:**
187 payload files, **6,943,739,779 bytes**. No incomplete or mismatched payload
remains in the transfer receipt. Desktop originals remain authoritative; this is
a replaceable HPC computational mirror, not archival storage. Scratch retention
is still a durability limitation, not a blocker to this authorized copy.

| Destination-relative component | Files | Bytes | Result |
| --- | ---: | ---: | --- |
| `s10-preparation-v2/` | 24 | 4,899,499 | Verified complete |
| `s10-mesh/` | 12 | 8,073,940 | Verified complete |
| `sct-v2/` | 137 | 1,446,987,796 | Verified complete |
| `raw/` | 1 | 5,483,600,151 | Verified complete |
| `receipts/external/` | 1 | 19,720 | Verified complete |
| `receipts/sct-v2/` | 4 | 74,765 | Verified complete |
| `receipts/s10-preparation-v2/` | 4 | 75,133 | Verified complete |
| `receipts/s10-mesh/` | 4 | 8,775 | Verified complete |

Control inventories/receipts below are additional to the 187 payload files.
Every destination payload was SHA-256/size checked independently on HPC before
and after promotion from `.incomplete`, then checked again in a final complete
inventory pass. Already transferred files and partial prefixes were authenticated
before reuse. A post-transfer rehash of all 187 desktop sources also passed.
No desktop source artifact was changed, and no installed Windows environment
was transferred.

The initial sessions stopped during verifier setup/verification and retained
partial files. Repeated SSH command channels caused repeated approvals; the
successful helper used one persistent remote verifier and one SFTP channel.
The final receipt includes authenticated files reused from those partial copies;
this is transport resumption, not scientific regeneration or reuse of rejected
scientific artifacts. Credentials were not written to scripts, repository files,
environment variables or transfer logs. No scientific HPC job was submitted.

### Receipt and inventory identities

All four files are at the HPC destination above. Byte-identical local copies:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\portability_20261103
```

| Control file | Bytes | SHA-256 |
| --- | ---: | --- |
| `source-inventory.json` | 71,037 | `8d5861b3ac76b4e4eaea5fd8d979cb360b3d425530d0b4faadb79a65b7f51a79` |
| `source-inventory.csv` | 46,075 | `b30c0a8562be6871e6edfb81c8e525310c17ea3346f2b228afa1fd8e30b30752` |
| `transfer-receipt.json` | 45,963 | `5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60` |
| `destination-verification.json` | 36,311 | `8254cd7d7a4e96665a667d6a226a636076944f6161646d7ea8ea62984e69ba65` |

The inventory preserves exact original machine-local paths and their mapping to
HPC-relative paths. Internal Windows provenance strings were copied unchanged;
they are not Linux runtime paths. Do not rewrite immutable scientific contracts
to pretend artifacts were generated on HPC. Resolve actual artifact paths
explicitly while retaining their authenticated identities.

Required payload identities:

- `s10-mesh/sampler-facing.npz`: 7,195,273 bytes;
  `69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0`.
- `sct-v2/run-manifest.json`:
  `03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f`.
- `raw/Johnston_MERFISH_Data.h5ad`: 5,483,600,151 bytes;
  `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`.

The S10 v2 package contains the exact 9,422-cell canonical response/mesh join,
prepared model input, two deterministic GPINIT fits and independent readbacks.
Its clean generating commit remains
`679a7432430464ba0031f9762b77e48f50946964`; registration and transfer do not
change the producer. K=20, nfit=250 and seed=2026102610 remain mechanical gate
settings, not production choices. Historical 4,712-cell artifacts are not
substitutes. See the [v2 receipt](initialization/audits/S10_fullcell_v2_20261103/receipt.json).

## Environment and scientific limits

Existing HPC sampler CPU environment:

```text
/work/abussing/bsfm-consolidation/environments/sampler-cpu-py311
```

The [passing Linux CPU audit](environment/HPC_SAME_ENVIRONMENT_VALIDATION.md)
records job 22012334: 75 tests and seven same-environment historical/port
comparisons. This is its bounded historical validation scope, not validation
of later Windows-only sampler layers, the WIP runner, or a GPU production fit.
Use platform-specific locks and receipts; do not copy Windows virtualenvs or
silently substitute dependency versions.

**Canonical Linux fmesher remains incomplete.** Job 22012400 timed out
(exit `1:0`, elapsed `02:00:09`, batch MaxRSS `902232K`); R and 20 packages
completed, with the retained log stopping in s2. Fresh package/version/isolation
validation and canonical Linux mesh reproduction were not reached. Preserve the
partial prefix. See the [terminal record](environment/HPC_R_MESH_BUILD_22012400.json).
The accepted Windows mesh and the transferred canonical mesh artifacts remain
valid within their recorded scope; this transfer does not reproduce them on Linux.

Full-data SCT at depth 124 is **ineligible for primary holdout scoring**.
The copied S10 preparation is full-data preparation. Future primary leave-out
experiments require approved training-only preprocessing/fitting/depth/centering
populations and an explicit scoring policy. Reuse the approved fixed-design mesh
for chunk holdouts; do not silently substitute historical responses or rebuild
geometry after removing observations. No leave-out workflow, scientific fit,
production K, chain count, or run lengths were selected by this task.

## Exact resume instructions on another computer

1. Inspect local Git status and preserve any local edits. Fetch GitHub; update
   clean main by fast-forward only. Read AGENTS.md and this handoff completely.
   Accepted Layers 1-8 remain on main. Inspect
   `review/layer9-portability-20261103` in a separate worktree; do not replace
   it with the older `wip/layer9-orchestration-20261103` draft or merge it
   automatically. The older draft and review receipts remain historical evidence.

2. The 187-file transfer is complete. If checking the mirror on reconnect,
   verify only the transfer-receipt identity unless a concrete integrity concern
   requires a payload recheck:

   ```sh
   ssh -p 222 abussing@login.rci.sc.edu
   sha256sum /work/abussing/bsfm-consolidation/canonical-artifacts-20261103/transfer-receipt.json
   ```

   Expected SHA-256:
   `5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60`.
   Do not repeat recovery, download raw data, regenerate preparations, or rehash
   all payloads merely because original Windows paths differ. A newly copied
   mirror still needs its own destination verification.

3. Read the current review branch's
   `docs/sampler/linux-review-20261103/REVIEW_RESULTS.md`, validation receipts,
   implementation/portability patches, inventory and source map. Distinguish
   full tests at a496b7c from the final storage guard at 8abee70. Preserve
   ordinary regression failures separately from passing historical comparisons.
   Do not relax fixtures/tolerances or rewrite accepted mathematical kernels.

4. The Linux runtime is the isolated
   `/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python`.
   Its committed run scripts record required modules, CPU/x64 and thread limits.
   Linux R mesh/SCT availability and scientific validation remain separate
   limitations. The old sampler CPU environment does not replace this runtime.

5. Complete the Layer-9 acceptance review, then prepare the separately bounded
   S10 mechanical integration using the transferred canonical full-cell input,
   mesh and GPINIT. Any HPC submission needs a committed specification and
   explicit approval under AGENTS.md. A full-data mechanical smoke is not an
   honest primary holdout experiment.

6. The subsequent vertical slice requires one deterministic hole, training-only
   SCT fitting/depth/centering, training-only GPINIT, the accepted fixed-design
   mesh, warped and matched identity-warp fits, and posterior prediction/scoring
   on identical omitted cells. No large section/hole-size grid precedes that
   working slice. No production K or run lengths are inferred from smoke settings.

Keep code/evidence synchronized to GitHub and exact HPC checkouts. Never store
credentials. Large data, environments, checkpoints and logs stay external with
recorded identities.
