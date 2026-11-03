# GPU correction, replay validation and fresh fits

The inherited repeated-index scatter caused same-input GPU gradients and
transitions to vary. A GPU-only fixed-incidence reduction now avoids conflicting
writes while preserving the likelihood and analytic gradient formula. CPU
arithmetic is unchanged. No scientific schedule or fixture tolerance changed.

## Evidence

- First gate **22015917**, correction `8dbff58`: PASS, 89 seconds. Ten full
  real-input gradients and same-key split transitions repeat exactly, including
  a newly compiled runner. Autodiff relative gradient error: 2.18e-13.
- Complete gate **22015934**, `51e1ee9`: PASS, 15m13s, exit 0. Three real-size
  K12/L14 strict and incremental transactions match exactly. After deliberately
  exiting between checkpoint-candidate and retained-record creation, a fresh
  process recomputed sweep 2 exactly and completed sweep 3 identically. Opening
  the completed run with a fail-on-sweep sentinel confirmed non-replay.
- Both gates reuse authenticated old adapted values as diagnostic inputs under
  explicitly recorded code identities. They do not repeat warmup, migrate old
  scientific chains, or establish convergence.
- Two local correction tests passed, including an independent dense Gaussian
  gradient. Eighteen CPU kernel comparisons plus the canonical split transition
  and audit match pre-change `51cd306` exactly in the same runtime.
- Broader Layer-3/5 suite: 35/41 passed. Five saved-reference failures and the
  existing Layer-5 provenance-map mismatch remain recorded; this is not a clean
  full-suite pass. Neither fixtures nor tolerances were rewritten.

Receipts: `FIXED_GRADIENT_GPU_VALIDATION.json`,
`ACCUMULATION_LOCAL_VALIDATION.json`, `FIXED_GRADIENT_FINAL_EVIDENCE.json`.
The last file is byte-identical to its HPC evidence mirror (120,944 bytes,
SHA-256 `b08135bdbdc7e8567435a42d71e5d9dedc6070fc1f84a5951c66857da6d73e87`).
It includes full external receipt/log hashes and submission commands. The complete
source-map amendment is in `docs/sampler/LAYER3_SOURCE_MAP.csv`.

## Bounded timings

Real input: 3,379 training cells, 166 active vertices, 371 mesh modes, K12/L14,
784 features, 91 genes and three types. Three sweeps per arm only.

| Arm | Post-compilation sweep seconds | Sweep-2 end to sweep-3 start | Total seconds |
| --- | --- | --- | --- |
| Strict, one BLAS thread | 42.040 / 41.389 | 27.800 | 257.006 |
| Incremental, one thread | 41.660 / 41.003 | 15.243 | 237.719 |
| Incremental, four threads | 42.140 / 41.511 | 15.731 | 242.183 |

Saving overhead decreased in this short comparison; sampler arithmetic time did
not materially change. Four-thread job **22016006** completed in 4m23s, exit 0;
it is a timing result, not a separate exact-replay gate. It offers no measured
benefit here, so fresh fits use one thread. Different nodes, limited repeats and
compilation/closure costs limit broad speed claims. Long-history numeric
validation scaling is addressed by the incremental store, not established by
three-sweep timing alone.

First four-thread attempt **22015984** failed before sampling while authenticating
a one-thread seed under four-thread BLAS. Its evidence is preserved. The retry
authenticates the seed under its original thread count before creating the new
four-thread diagnostic contract; no hash check was skipped.

## Fresh scientific runs

Generating commit: **`f7ce41405fbc8ef4c1d0a84b50edc2611efd6780`** on the review
branch. All eight jobs were RUNNING, passed the complete-replay deployment guard
and explicit `cuda:0` startup check, and entered initial tuning. This is a startup
observation, not a completion claim. The review branch was not merged into main.

| Configuration | Deep | Flat |
| --- | --- | --- |
| 12 circles, diameter width/16 | 22016018 | 22016019 |
| 12 circles, diameter width/8 | 22016020 | 22016021 |
| 8 circles, diameter width/16 | 22016022 | 22016023 |
| 8 circles, diameter width/8 | 22016024 | 22016025 |

One V100, four allocated CPUs, 16 GiB host RAM and 12-hour cap per job; one BLAS
thread. Existing full mesh/prepared hole inputs and K12/L14 are unchanged.
Schedule: 50 initial tuning steps/factor, 50 bridge sweeps, 100 retuning
steps/factor, 1,000 production sweeps. Save/checkpoint every completed sweep.
Bridge draws are not production predictions. A wall limit may require continuation
from the same generating commit; it does not erase committed draws.

Logs: `/work/abussing/bsfm-consolidation/evidence/fixed-holey-JOBID.log`.
Output base:
`/work/abussing/bsfm-consolidation/evidence/holey-gpu-f7ce41405fbc8ef4c1d0a84b50edc2611efd6780-fixed-order`.
Then `CONFIGURATION/MODEL/{bridge,production}/segments/segment/transactions`.
Every published transaction directory contains its checkpoint and retained record.
Original jobs and outputs remain separate; do not pool same-seed duplicates.
The launch specification is `FRESH_GPU_RUN_SPEC.json`; `fresh_gpu.sbatch` refuses
deployment without PASS and byte-identical sampler/runner source versus the gate.

Next: inspect actual tuning/divergence progress and saved production counts before
constructing predictions. Mechanical gates do not establish scientific mixing,
posterior accuracy, or a guaranteed finishing time.
