# GPU workflow consolidation: staged evidence audit

Status: **in progress; not a claim of a corrected production runner**. Requested by the user on 2026-11-03 after observed GPU throughput exposed an orchestration problem. Review branch: `review/gpu-workflow-consolidation-20261103`, starting at execution commit `ac886d7`. Running scientific jobs remain on their original immutable commits. No historical driver is imported wholesale or executed as a program.

## Authority and evidence

The repository decisions remain authoritative. Historical code, conversations, manifests, scheduler records and actual outputs provide different evidence; none silently overrides an accepted scientific decision. The earlier recovery was explicitly bounded to source/architecture nomination and component comparisons. It did not establish end-to-end GPU performance. The missing gate is operational equivalence of the assembled workflow, not wholesale invalidation of the accepted numerical work.

Two historical HPC roots were inspected directly:

- `/work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024`
- `/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1`

Both selected drivers are 94,890 bytes with SHA-256 `eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`, exactly matching the canonical recovery ledger. Their common source does not mean their data, meshes, settings, environments or executions were identical. The October 26 package's cloud readiness is not evidence of a completed cloud fit.

External source capture: `C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/gpu-workflow-audit/historical-source.json` (61 files' contents and identities). Transport gzip SHA-256: `50bcb6812e590d448d833baf8d937986d3ff437ccada3eabe1eb40e9a8cd2403`. Originals were read, not modified. Source inventory and verification are separate tracked receipts; large/raw conversation histories remain external.

Local October/November conversation index: 49 matching sessions, 788 matching messages. This is a targeted keyword index, not a claim of exhaustive conversation review. Some user messages quote earlier assistant statements; those are historical claims, not new user approvals. The relevant October 26 original conversation is `C:/Users/andyb/.codex/sessions/2026/10/26/rollout-2026-10-26T11-44-46-01a00719-4968-7a51-8514-d08d0819e286_01a178e2-b6d5-7a73-a9ed-73d70e0a75a0.jsonl`: lines 891, 1113 and 1133 describe actual scheduling problems, preserving GPU allocation through all stages, and accidental cancellation scope. The October 27 refresh conversation refers to S00 production through sweep 465; current historical files extend beyond that snapshot. No conversation excerpt is treated as a successful numerical test.

## Stage ledger

| Stage | Recovered practice / invariant | Current evidence and disposition | Gate before promotion |
| --- | --- | --- | --- |
| Inputs, genes and cells | Authenticated preparation; 91 genes; explicit cell/type/order joins; quarantined invalid older panels | Preserve accepted SCT/mesh/GPINIT. Current hole experiment explicitly authorizes full-sample SCT, training-only centering/GPINIT/fitting, full mesh | No data recovery or regeneration. Verify actual run manifest joins; do not replace with older K20/75% inputs |
| GPU environment and allocation | CUDA/GCC/runtime compatibility; one GPU; fail on incompatible devices; retain allocation across stages | Existing historical environment reused; current launcher checks GPU/x64. Current `experiment.run` performs bridge and child production within one allocation | GPU startup/transition evidence is bounded, not full-chain equivalence. Keep exact runtime inventory and tested device route |
| Initialization and RNG | GPINIT seeds, alpha floor, PX, noise prior, natural factor order and retained endpoints | Existing Layer-9 literal initialization/RNG tests are evidence; no source change proposed | Recheck against authenticated driver whenever changing composition |
| Adaptation | Sequential endpoint propagation, split field/fixed-W hyper blocks, frozen tuning | Historical source also chunks adaptation; do not label existing chunking a new optimization. Fresh 50/100-step same-runtime comparison in `check_transition_lineage.py` | Exact leaf/history/tuning comparison; separate CPU from GPU evidence |
| Gibbs chronology | Three loading/joint-eta/noise subcycles; shrinkage/PX; random factor order; split field then fixed-W hyper, one eta redraw | Accepted Layer-6 source map traces selected driver. Fresh literal chronology comparison includes state, diagnostics and RNG | Do not redesign numerical kernels to hide orchestration cost |
| Bridge/readaptation | Preserve complete endpoint; new stage with explicit schedule and RNG policy; distinguish settling from production | Current user-authorized schedule 50 tuning / 50 bridge / 100 tuning / 1000 production; one allocation | Historical stage-two .95 is explicitly superseded by accepted .9. Do not silently restore .95 |
| Durable state and restart | Complete atomic latest checkpoint; preserve spectral chart, tuning and RNG | Canonical design strengthens historical saving with atomic checkpoint+record transactions, separate genesis, no committed replay | Preserve these guarantees. Historical overwrite of latest checkpoint is not a reason to remove canonical transaction integrity |
| Normal-loop publication | Historical driver advances in-memory state and writes current checkpoint; does not restore all prior states every sweep | **Confirmed regression:** current controller scans all transactions, revalidates all checkpoint/record pairs, repairs all projections, constructs a full archive and revalidates that archive again each sweep | Incremental single-writer path requires an explicit design amendment and interruption/corruption tests; no silent validator bypass |
| Diagnostics / fidelity | Per-sweep timing, acceptance/divergence/leapfrogs, PCG/PX/warp invariants; distinguish finite-feature likelihood from exact-SE diagnostics | Current external performance receipt times sampler only; console omits ordinary sweep progress. Historical fidelity diagnostics are not all implemented canonically | Add stage timing/progress without changing scientific record/RNG. Decide and document diagnostic coverage; no convergence claim |
| Retained draws / prediction | Complete reconstructable states; native factor coordinates; no pooling bridge with production or duplicate same-seed submissions | Meeting snapshot uses conditional held-out prediction and all selected production draws; reports preprocessing limitation | Verify reconstruction, matched flat/deep target conditions, gene/cell identities and held-out scoring separately |

## Actual historical execution evidence

`RUNTIME_EVIDENCE.json` records inspected paths, byte hashes, sweep counts and timing summaries. Two first-chain files reach 1,100 total / 1,000 production sweeps: S00 and S03. Both have `COMPLETE_WITH_FIDELITY_WARNINGS` certificates, not an unqualified PASS or convergence certificate. S00's final-20 median sampler timing is about 119 s and S03's about 155 s. These are K20/75%-cell historical fits with different meshes/settings, not matched benchmarks for today's K12/L14 holes. S00's certificate records finite-feature-vs-SE fidelity warnings; exact-SE certification is not implied.

The earlier recovery's scheduler capture of no completed campaign jobs was a historical snapshot. These later on-disk outputs add evidence; they do not retroactively change what that earlier audit inspected. Completion certificates must still be distinguished from independent chain-state/diagnostic validation.

## Measured current bottleneck

The read-only timing snapshot includes all four current flat and four deep bridge roots. For the initial inspected 12-hole, diameter-1/8 pair, flat sampler timing was approximately 20 s while transaction directory publication intervals were 290–326 s. Deep sampler timing was approximately 44–48 s while publication intervals were 148–200 s. Directory mtimes are an observed publication-interval proxy, not a separately instrumented profiler. They include validation, writing and other inter-sweep work. No fixed GPU speedup is inferred.

Source explains a growing repeated cost: `RunController.run` calls `Transactions.scan` on every loop; `scan` calls both public checkpoint and record validators for every historical transaction; `repair` rehashes all projections, constructs `RetainedArchive` (full validation) and calls `require_resume_boundary` (another full validation). New-pair validation and checkpoint serialization add further work. Thus repeated historical validation alone scales quadratically over a complete run. This is not explained by K alone.

The Layer-9A design explicitly requested reopening the archive and its continuity/resume checks at each publication. The performance problem is therefore partly a design omission, not merely a typo. A correction must document the revised validation lifetime rather than pretending to preserve the old wording unchanged.

## Next bounded correction gate

Fresh local numerical lineage result: **PASS**, recorded in `TRANSITION_LINEAGE.json`.
The 50-step and 100-step adaptation outputs (all leaves, histories and tuning),
the Layer-5 Gaussian/canonical transition comparison, and the Layer-6 literal
driver chronology comparison were exactly equal in the same CPU runtime.
Elapsed time was 425.16 seconds. This verifies the bounded synthetic numerical
composition, not GPU throughput or a scientific posterior fit. Source identities
and environment versions are included; committed reference fixtures were not edited.

The captured-source verification also passed: 61 files' text/size/SHA identities
and eight selected sampler-file copies (four filenames in each HPC package).
See `SOURCE_INVENTORY.json`. The verifier selects the exact nominated source root,
not an ambiguous basename from the multiple historical driver rows.

1. Preserve full validation at startup/resume and final closure. Retain all per-sweep transactions and every new pair's public Layer-7/8 validation and post-publication readback.
2. During an uninterrupted exclusive writer lease, advance a validated in-memory chain and validate only the newly published pair/projections numerically. Define explicit detection of mutation to previously accepted files and fail closed; do not claim protection against arbitrary external writers or bit rot beyond the checks actually performed.
3. Keep accepted Layers 1–8 and their public strict readers unchanged. Any incremental projection view belongs in orchestration and must not masquerade as a fully reopened archive.
4. Prove exact uninterrupted/interrupted state, tuning, all RNG streams and records; committed non-replay; incomplete attempt recomputation; projection repair; corruption rejection; and bounded per-sweep validation counts as history grows. Record sweep, serialization, validation and publication timing separately.
5. Test under the supported HPC filesystem/GPU runtime with a bounded committed specification. Existing scientific jobs remain untouched until an explicit, verified continuation mechanism bridges their old code/software identity to the corrected version. Editing a running checkout or silently changing its immutable spec is prohibited.

No optimization is declared validated or deployed by this audit document. No new scientific run, environment build, mesh regeneration or accepted-layer rewrite is part of this evidence gate.
