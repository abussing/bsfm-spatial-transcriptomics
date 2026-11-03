# Split-NUTS to real-data/Wasserstein execution lineage

## Result

The inspected split-NUTS experiment, the October real-data campaign, and the saved states used for the October 27 Wasserstein refresh form a connected, authenticated lineage. This comparison does **not** reveal a discarded faster split-NUTS mathematical kernel. It does reveal operational differences and a confirmed saving/validation regression. It does not establish that every historical experiment has been assessed or that current end-to-end performance is optimal.

## Verified joins

1. The `area_wasserstein_analytic_20261027_v1/export_refresh_snapshot.py` source identifies `bsfm_19section_production_20261024` as its source campaign. The frozen `refresh_snapshot_20261027_1035/SNAPSHOT.json` records 11 sections, their source run directories, selected sweeps and draw hashes.
2. For **all 11 sections**, the actual frozen `C3FULL_POSTERIOR_DRAWS.npz` bytes match both the snapshot hash and the Wasserstein refresh's `COMPLETION_AUDIT.json` draw hash. Selected sweeps match too. This verifies the frozen snapshot, not whatever later state a live campaign directory acquired.
3. Each of those 11 source runs' `code_manifest.json` records production driver SHA-256 `eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`, the selected canonical recovery source. A recorded source manifest is provenance evidence, not proof that historical directories were immutable throughout execution.
4. Nine source files in `split_paint10_L16_v1` match the production campaign byte-for-byte and match the split experiment's own `SPLIT_SOURCES.json`: `full_split.py`, `joint_eta_pcg.py`, `fixed_splusu_dynamic_target.py`, `centered_hyper_target_qr.py`, `spectral_live_range_whitening.py`, `active_marginal_whitening.py`, `direct_w_dynamic_target.py`, `c3_established_functions.py`, and `restart_state.py`.
5. The split experiment's historical `validation/PASS.json` authenticates that same source-manifest hash. It reports five full Gibbs sweeps plus checkpoint replay, N=2500/L16, and explicitly makes no sampling-quality claim. This audit read that receipt; it did not rerun the historical program.
6. The current `split_kernels.py:build_split` syntax tree matches historical `full_split.py:build_split` exactly after excluding the explicit GPU acceptance-roundoff guard. That comparison retains decorators and all remaining function statements. Existing canonical source maps and the fresh `TRANSITION_LINEAGE.json` provide the selected-source-to-port mathematical and synthetic numerical checks.

The 11-section snapshot contains **four production states and seven adaptation endpoints**. It must not be described as 11 converged production fits. S00's selected production sweep was 465; S03's was 220; S10's was adaptation endpoint 101. The separate original S03 Wasserstein benchmark has its own manifest; the 11-way join specifically establishes the refresh lineage.

## Driver differences actually inspected

The complete split-to-production driver diff is retained in `EXECUTED_LINEAGE.json`. Changes add explicit checkpoint readaptation, retained shrinkage variables and physical warp arrays, corresponding reporting/CLI handling, and a guard limiting the initialization containment rejection to enabled containment. The nine mathematical dependency files are unchanged. This is stronger evidence than recognizing optimization names in current code, but is not a new equivalence claim for every optional historical flag.

The current source retains the analytic finite-feature derivatives, custom-VJP BlackJAX bridge, feature-space Gaussian algebra, JIT split transition/scan, full-spectrum active marginal QR, and block-preconditioned joint-eta PCG described in `OPTIMIZATION_COVERAGE.md`.

## Operational differences to measure

| Aspect | Historical executed-path evidence | Current path | Disposition |
| --- | --- | --- | --- |
| CPU/BLAS threads alongside GPU | Split submission requests 4 CPUs and sets BLAS/OMP/MKL to 4; K20/75% wrappers use allocated CPU count, default 4 | Recorded GPU runtime authentication enforces one BLAS thread | A concrete configuration difference; benchmark representative conjugate/validation work before changing environment authentication. No assumed speedup. |
| Retention cadence | K20/75% adaptation saves its final endpoint; production retains every 5 sweeps | Hole experiment retains every sweep at user request | More storage work is expected; do not silently reduce requested saved output. |
| Saving/validation | Historical driver advances live state and overwrites an atomic latest checkpoint; retention archive is separate | Original canonical controller revalidates all old transactions and archives each sweep | Confirmed regression; opt-in incremental candidate has passed synthetic GPU checks. |
| GPU environment | CUDA 12.3, GCC 12.2, x64, existing `arka_trying_gpu_again/env` | Same environment path is recorded/authenticated for GPU execution | Historical path reuse is not by itself historical package-byte equivalence. Current runtime receipt supplies current identity. |
| Run settings | K20/75% cells/L16; production wrapper target acceptance .95 after .9 adaptation | K12/50% hole subsets/L14, accepted .9 | Different workloads and tuning; historical elapsed times are not a matched benchmark. Do not silently restore .95. |
| Diagnostics | Historical fidelity, scale-feedback and scoring cadence | Canonical diagnostics differ; ordinary sweep progress is sparse | Document coverage separately from transition speed; do not erase warnings to improve timing. |

## Evidence and reproducibility

- `EXECUTED_LINEAGE.json`: 219 captured-source identities, 11 draw joins, nine kernel comparisons, split validation receipt and driver diff. Exact external receipt SHA-256: `0fa4dd650b83bc4343604ee29e99a5eed1507051d4e59d733ff98e1d23dc0607`.
- `EXECUTION_SUPPLEMENT.json`: actual K20/75% wrapper source, 11 code-manifest joins, and the full successful GPU gate receipt. External SHA-256: `bfd6eca09bccdd48c5e2b7a63e0dc2c8265e188c921263e70fb911d12a90b175`.
- External full text capture: `/work/abussing/bsfm-consolidation/evidence/gpu-workflow-audit-20261103/extended-lineage.json`, 2,502,189 bytes, SHA-256 `867811f3223ac04275387b24fe82e9b232bd10e7b168a51e219ed0f123ce7c48`.
- Both compact receipts are mirrored locally under `C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/gpu-workflow-audit/` and in this directory. Source captures are evidence, not executable imports. No historical script was run and no scientific job was changed.

GPU gate 22015748 completed successfully in scheduler elapsed 00:02:07. It exactly matched three strict/incremental transaction receipts, recomputed an uncommitted sweep after candidate process death, and prevented committed replay. Its tiny synthetic timings do not establish representative throughput.

## Decision and remaining scope

Retain the selected split-NUTS numerical path for the representative performance comparison: the inspected evidence does not justify replacing it with a guessed historical alternative. Prioritize measuring orchestration/validation, host threading, host/device transfers and compilation alongside the actual GPU kernels. Fresh fits are acceptable; migration of old checkpoints is not a prerequisite.

Earlier RMHMC and real-data QR/flight bundles were located and their small source records inventoried. Their comparative sampling performance has **not** been established here; they must not be labeled faster or promoted based on folder names. The accepted exclusion of LI/Fisher experimental transitions remains unchanged. This report completes the specific split-paint -> production -> Wasserstein-refresh lineage check, not an exhaustive certification of every experiment over several months.
