# Current BSFM handoff

## 2026-11-04: narrow consolidation cleanup

Continue from [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md), the single current method
map. Extend existing layer boundaries; do not introduce a parallel pipeline
framework or competing current guide. The draft wrapper and duplicate guide
were removed before publication. Axolotl/CELINA evidence is folded into the
existing dataset contract. A bounded recovered screening GP and biological
aggregation fill the upstream selection gap; their source and test scope are
recorded in the workflow guide. Core mesh, GPINIT and sampler implementations
are unchanged. Generic execution remains incomplete. Leave-out experiment work
is separate from the current core-interface cleanup.

## 2026-11-04: dataset/response foundation implemented

Read [the dataset contract](preprocessing/DATASET_CONTRACT.md) and
[validation receipt](preprocessing/DATASET_LAYER_VALIDATION.json).
The portable NPZ/manifest format, explicit RData adapter and generic train/scoring
response exporter are implemented. Four focused tests pass. Real axolotl import
preserves 16,586 genes, 4,410 cells and six broad groups; independent sampled R/CSV
readback passes. Data remain external at the receipt's local path, not on HPC
yet. No gene/group selection, GP fitting, mesh construction or scientific run
was performed. The original SCT pipeline and running S10 source remain intact.

## 2026-11-04: reusable workflow consolidation requested

The user requires repository methods/rationale and configurable new-dataset
workflows, not only Johnston fixtures. Read [WORKFLOW_GUIDE.md](WORKFLOW_GUIDE.md)
for the audit, completed first increment and remaining implementation order.
The 91-gene rationale is recovered and reproduced exactly. New reusable selection,
library normalization, training-only centering and order-configured quadrature
loading pass six focused tests. Existing S10 source checkouts and sampler kernels
are unchanged. Generic end-to-end execution and axolotl fitting remain unfinished.
Axolotl source: `E:/axolotl/artista_data.RData`, SHA256
`37287f741ddbd899ff7590143c8985d2d20588e6b32bab0879e93298c589c8cf`.

## 2026-11-04: deep-chain continuation submitted

The four flat fits completed 1,000 production sweeps and 101 scored draws each.
The deep fits reached the 12-hour time limit with saved production boundaries
670, 830, 670 and 850 (configurations in the order listed below). Their prediction
summaries contain 68, 84, 68 and 86 draws. Saved outputs remain intact.

The user authorized continuation. The original clean generating commit and
committed launcher are reused, with identical output roots, resources, settings,
and the original target of 1,000 production sweeps. No fresh warmup is intended;
resume authenticates existing boundaries and recomputes only the unsaved tail.

| Configuration | New deep job | Resume boundary |
| --- | --- | --- |
| circles12_diameter1of16 | 22018064 | 670 |
| circles12_diameter1of8 | 22018065 | 830 |
| circles8_diameter1of16 | 22018066 | 670 |
| circles8_diameter1of8 | 22018067 | 850 |

[Submission receipt](recovery/gpu-workflow-20261103/PERIODIC_RESUME_20261104.json)
records commands, exact commit and saved-boundary receipt hashes. The same receipt
is preserved on HPC at `evidence/gpu-workflow-audit-20261103/periodic-resume-20261104.json`.
Convergence remains unassessed. Older running-job statements below are historical.

## Periodic-saving replacement: eight V100 fits running

The user requested stopping all BSFM jobs and relaunching with inexpensive
periodic saving and leave-out metrics. All 24 active BSFM jobs, including
22016018–22016025 and the older 16 alternatives, were canceled. Files remain.
The remaining `cs-*` jobs are a separate centering simulation and were not touched.

Candidate `2551f6d3c71be8956ab5d6f649371a2ad4615342` adds compact periodic
checkpoints/draws (first, every10, final), no duplicate projections, and an
independent streaming predictive-density scorer. Seven focused local tests pass.
Real GPU gate **22016122 PASSED**: exact numerical/RNG agreement with the previous
every-sweep run, exact interrupted restart, completed non-replay and actual
held-out predictive scoring with no double-counting on scorer restart.
Eight replacement jobs **22016141-22016148** are RUNNING and have entered
initial warmup, from clean generating commit
`cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414`. Read
[the policy and committed validation specification](recovery/gpu-workflow-20261103/PERIODIC_SAVING.md).
The [completion evidence](recovery/gpu-workflow-20261103/PERIODIC_FINAL_EVIDENCE.json)
records cancellation, validation and the exact configuration/job map.
Fresh roots are `evidence/holey-periodic-cfb9e4a7ec8ba0934aef71a71dcbf7950d8ad414/CONFIGURATION`
under `/work/abussing/bsfm-consolidation`. Production prediction summaries are
`predictions/MODEL/latest.npz` under each root. No production draws or convergence
are claimed at this startup checkpoint. Fixed geometry remains in genesis;
measured boundary checkpoint is 434 KB and retained draw 1.1 MB, saved first,
every ten sweeps and final. Old outputs remain preserved.
Do not use the older running-job statements below as current state.

## GPU correction passed complete replay; eight fresh V100 fits running

Read [the completed correction and fresh job map](recovery/gpu-workflow-20261103/FIXED_GRADIENT_RESULTS.md).
Jobs **22016018–22016025** were all RUNNING and passed CUDA startup checks.
Generating commit: `f7ce41405fbc8ef4c1d0a84b50edc2611efd6780`; fresh output
tag `fixed-order`. They use K12/L14, the four approved hole configurations,
deep/flat pairs, the agreed 50/50/100/1000 schedule and save every production
sweep. Existing old scientific jobs/outputs were not changed. Do not pool
same-seed duplicates. No completed production draws or convergence are claimed
for these fresh runs at this checkpoint.

The GPU-only fixed-incidence reduction at `8dbff58` passed job **22015917**
(89 seconds, exit 0): ten full gradients exact, same-key split transitions exact
with both reused and newly compiled runners. Independent autodiff gradient
relative error was 2.18e-13. CPU arithmetic is unchanged in 18 same-runtime
kernel comparisons against `51cd306`. Read
[the correction and bounded next gate](recovery/gpu-workflow-20261103/ACCUMULATION_CORRECTION.md).
The complete receipt is `FIXED_GRADIENT_GPU_VALIDATION.json` in that directory.

Complete-sweep/restart gate **22015934**, commit
`51e1ee91d6cb3e54ce0e80baaaaa1c99e891c000`, PASSED (15m13s, exit 0).
It uses authenticated saved real K12/L14 input as an explicitly labeled diagnostic
seed under a new software contract; no warmup or scientific checkpoint migration.
Output: `/work/abussing/bsfm-consolidation/evidence/real-replay-22015934`.
All three strict/incremental transactions matched exactly; a fresh process
recomputed interrupted sweep 2 exactly and completed sweep 3 identically.
Completed-run non-replay passed. Full evidence and timing/failed-attempt identities
are in `FIXED_GRADIENT_FINAL_EVIDENCE.json`. Four-thread timing 22016006 completed
without useful improvement; fresh fits keep the replay-tested one-thread setting.

Local focused correction tests passed (2/2). Broader Layer-3/5 tests recorded
35 passes and six failures: five saved-reference comparisons and the existing
Layer-5 split-kernel source-map mismatch from the prior GPU roundoff amendment.
See `ACCUMULATION_LOCAL_VALIDATION.json`; fixtures/tolerances were not relaxed.
The earlier failed strict/incremental test below remains preserved evidence.

## Representative failure diagnosed: inherited GPU scatter nondeterminism

Job 22015787 failed exact strict/incremental comparison after both one-thread
arms completed; the four-thread arm never ran. Do not treat it as a successful
performance/production gate. Read
[diagnostic findings](recovery/gpu-workflow-20261103/REAL_TIMING_DIAGNOSIS.md).
GPU probes 22015888 and 22015895 completed and reproduced different results from
the same compiled transition with identical inputs/key, independently of saving.
The inherited repeated-index gradient scatter-add is itself nondeterministic on
the actual input. A fixed-order operator probe repeated exactly ten times, but
the full gradient/transition with that correction is not yet validated or deployed.
Receipts, original failure, hashes and evidence paths are preserved in
`GPU_NONDETERMINISM_EVIDENCE.json`. Next: narrowly correct deterministic accumulation,
verify mathematical equivalence and full-size GPU replay, then resume timing and
fresh-fit selection. Do not silently weaken exactness checks. No scientific jobs
or production numerical kernels were changed by these diagnostics.

## GPU integration and representative timing submitted

Commit `9fb50b3` integrates incremental saving into the GPU entry for bridge and
production stages and explicitly authenticates one or four BLAS threads (scientific
entry still defaults to one). This changes fresh execution from this commit only;
existing scientific checkouts remain unchanged. Read
[runner integration](recovery/gpu-workflow-20261103/RUNNER_INTEGRATION.md).
Representative real-input GPU job **22015787** was submitted with K12/L14, 20 tuning
steps/factor and three sweeps/arm, strict versus incremental and one versus four
threads. Its [submission record](recovery/gpu-workflow-20261103/REPRESENTATIVE_SUBMISSION.json)
contains exact limits, commit and evidence paths. No result or full-size speedup
has been established at this checkpoint. Review its receipts before choosing
threading and launching fresh scientific replacements. Old outputs are preserved.

## Executed split-NUTS and Wasserstein lineage verified

Read [the executed-lineage report](recovery/gpu-workflow-20261103/EXECUTED_LINEAGE_REPORT.md).
Eleven frozen Wasserstein-refresh states match their source snapshot hashes and
sweeps; their source-run manifests name the selected production driver. Nine core
split-experiment files match the production dependencies exactly. The current
split transition matches the historical function apart from its documented GPU
roundoff guard. This does not certify every historical experiment or full-size speed.

Synthetic GPU gate 22015748 passed at commit `fc08d6e`; its complete receipt is
in `EXECUTION_SUPPLEMENT.json`. The incremental store remains opt-in and is not
selected by the scientific launchers. The user now prioritizes recovering the
optimized execution path over preserving completed iterations or avoiding warmup;
code-version checkpoint migration is deferred. No scientific job was changed by
this lineage audit. Remaining representative timing must include host threading,
validation, serialization, compilation and GPU transitions.

## GPU workflow consolidation audit, 2026-11-03

The user requested renewed stage-by-stage consolidation of historical practice,
recent conversations/submissions and the current GPU workflow. Read the
[staged evidence audit](recovery/gpu-workflow-20261103/AUDIT.md) on
`review/gpu-workflow-consolidation-20261103`, based on execution commit `ac886d7`.
Accepted main was separately fetched and remains `c42e058` at this inspection;
this review branch does not promote Layer 9 to accepted main.

Source capture verification and fresh same-runtime 50/100-step adaptation,
split transition and literal Gibbs chronology checks passed. Repeated full-history
transaction/archive validation is a confirmed orchestration scaling problem.
An incremental storage candidate is under local fault testing, not enabled in
any launcher and not deployed. Preserve strict resume/publication/RNG guarantees;
do not edit current jobs' immutable commits or software contracts.

The user authorized cancellation of the six remaining CPU hole jobs and both
P100 jobs; cancellation was confirmed. Their saved data remains. The eight
primary V100 jobs (four flat, four deep) were still RUNNING during this audit.
Other same-seed queue alternatives must not be pooled as independent chains.
The meeting flat snapshot is preserved under `evidence/meeting-flat-922a558`
on HPC and described in `docs/holdouts/s10-grid-20261103/MEETING_RESULTS.md`.

Older sections below are chronological evidence and do not supersede this audit.

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
- No S10 or leave-out run has yet been submitted by this checkpoint.

The next proposal uses only 24 cells, two sliced GPINIT factors, 20 warmup steps
per factor (the supported minimum), and two sweeps with a fresh-process restart,
under a ten-minute cap. It first gates on same-runtime Layer-4 comparisons and
an exact chart-boundary probe. Full-data SCT/GPINIT remain ineligible for primary
holdout scoring; the subset is a labeled execution derivative, not new canonical
preparation or a full-cell validation. No mesh or GPINIT regeneration is proposed.

## Linux Python environment completed

Job 22013408 at `460ccdd6ca523d22f2c61c0cbacdf0f1f82ba0de` completed the isolated
Linux environment build. All 13 runtime versions, dependency checks, CPU/x64
and module-path isolation passed. See the [environment receipt and history](environment/layer9-linux-20261103/README.md).
This does not validate the Layer-9 runtime on Linux or authorize scientific
fits. Windows-only writer locking and environment authentication still require
a reviewed Linux implementation and synthetic continuation validation.

## Continuation update: Layer-9 review publication, 2026-11-03

The verified artifact transfer below remains complete. No recovery was repeated.
New continuation work is preserved on `review/layer9-portability-20261103`,
based on accepted main `eeb6d9a903663907bbcb2d081bcec05475788ee1`.
Read [the publication record](sampler/review-layer9-20261103/PUBLICATION.md)
and [review package](sampler/review-layer9-20261103/README.md).
Layer 9 remains a reviewed candidate, not accepted scientific functionality.

Local Windows evidence: 36 expanded Layer-9 tests passed; a subsequent strict
saved-modal domain guard passed five focused tests and an exact retained-genesis
restoration check. Five synthetic runtime-input join checks also passed.
The ordinary accepted-layer suite ran 195 tests with eight saved-fixture failures;
separate authenticated same-environment original/port comparisons passed for
Layers 1-3, 5 and 6. These distinct results are preserved, not relabeled.
Canonical mesh checks: seven passed, one R-dependent integration test skipped.
Accepted source/tests/config/environments were checked byte-for-byte unchanged.

The bounded Linux environment-build proposal is included with exact-version
platform wheel identities. Its installation and later Linux numerical/runtime
validation are separate milestones. No S10 or leave-out scientific job has been
submitted by this publication. Training-only holdout preprocessing, the matched
flat model and posterior prediction/scoring remain outstanding.

The remaining text records the accepted shutdown baseline and original WIP.

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
