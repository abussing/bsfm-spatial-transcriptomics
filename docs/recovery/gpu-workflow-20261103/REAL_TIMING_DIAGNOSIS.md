# Representative timing failure: diagnosis in progress

Job 22015787 failed after 25m50s at exact transaction comparison. Both one-thread arms completed all three sweeps; four-thread execution never started. Do not mark representative validation passed or launch fresh replacements on this evidence.

Read-only inspection of saved files established:

- Strict and incremental genesis NPZ files are byte-identical.
- First-sweep checkpoint RNG records match exactly. Loading, noise, phi, delta and tau arrays also match exactly; eta, alpha, zeta and positions differ.
- First-sweep PCG diagnostics, PX diagnostics and factor visitation order match exactly.
- The first visited factor is factor-011 (zero-based index 10). Its transition audit inputs, including full context, input-position hash and random key, match exactly. Only `maximum_W_relative_error` and `output_position_sha256` differ in that transition audit.
- First-factor momentum, divergence flags and leapfrog counts match; field acceptance differs by approximately 1e-12 and field energy by approximately 5e-12. These first diagnostic differences are small, but later state differences are not dismissed as harmless: after sweep 1, maximum position difference is about .0232; after sweep 3 it is about 5.49.
- The first differing transition therefore occurs before transaction publication. The evidence does not yet identify whether GPU nondeterminism, compilation differences, an input property not covered by hashes, or another mechanism causes it. Do not label this merely a compression mismatch or relax equality checks.

Array difference receipt remains at `evidence/gpu-workflow-audit-20261103/real-timing-array-differences.json` on HPC. Original failed outputs remain untouched at `evidence/real-timing-22015787`.

## Approved diagnostic scope

The user explicitly requested diagnostics. `diagnose_transition.sbatch` bounds the next isolation to one V100, four CPUs, 16 GiB host RAM, maximum 15 minutes. It reads/authenticates the original strict genesis and exact spectral chart, performs the preceding conjugate/PCG/PX work once, and intercepts the first factor transition. It repeats that transition with identical key/state/context in the same compiled runner, then in a newly constructed runner. It records exact comparisons, first-factor input arrays and differences against the original saved positions. It stops before the rest of the sweep, performs no warmup, and writes no scientific checkpoint. This is diagnostic execution, not a production retry or a change to sampler tolerances.

The original software contract is used only to authenticate the saved source state. The diagnostic's own generating commit is recorded separately. Current scientific runs remain untouched. Syntax/whitespace preflight passed; numerical diagnosis is pending GPU execution.
