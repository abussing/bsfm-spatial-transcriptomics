# GPU runner integration and representative timing

User approved implementing the proposed execution correction, comparing representative GPU/thread throughput, and using verified settings for fresh fits (2026-11-03). Current scientific jobs are not edited or cancelled. The large replacement fit launch remains dependent on measured results.

The GPU scientific entry now explicitly selects `IncrementalTransactions` for both the initial bridge and readapted production child. The storage policy is included in the run-configuration identity. Strict public readers and original `RunController` defaults remain available; existing immutable scientific checkouts are unchanged. Both paths retain every requested saved draw. Scientific schedule, factors, quadrature order and targets are unchanged.

GPU authentication accepts an explicit `blas_threads=1` or `4`, verifies the actual installed BLAS pools match, and records that setting in the environment identity. Scientific entry still defaults to one thread until measured results support a different selection. Four threads are not silently accepted as an exact continuation of a one-thread run.

Validation: changed Python files compile; diff whitespace checks pass. Using the actual new integration helper, a copied authenticated completed synthetic archive reopened with an exactly matching completion receipt and a fail-on-sweep sentinel proved no replay. The underlying incremental implementation is unchanged from GPU gate 22015748. These checks do not substitute for representative performance or a new production fit.

## Committed representative run specification

Entry: `representative_timing.sbatch` and `representative_timing.py` in this directory. One V100 on `v100-16gb-hiprio`, four CPUs, 16 GiB host RAM, maximum 90 minutes, using the existing recorded GPU environment. Scope is the real prepared S10 50%-cell subset with 12 circles of diameter width/8, K12, L14, 91 genes, three cell types and the already prepared full mesh. No data preparation or artifact regeneration.

For each of one and four BLAS threads, perform 20 initial tuning steps per factor and three deep-model sweeps with strict saving. Copy the authenticated adapted genesis into a separate incremental arm and run the same three sweeps, checking all transaction receipts exactly. Each thread setting starts its own process and independently tuned state; cross-thread exact numerical trajectories are not assumed. All outputs are under a new `evidence/real-timing-JOBID` root, not scientific production directories.

Record initialization/warmup, sweep and publication events and completion receipts. Strict executes first, so compilation/cache order is unbalanced; do not report total-runtime ratios as pure saving speedups. Use post-sweep-to-next-sweep intervals to inspect overhead and post-compilation sweep timings to inspect threading. Three sweeps do not demonstrate long-history scaling; the separate bookkeeping count test supplies only algorithmic validation-count evidence. Print phase progress and write intermediate timing receipts after each completed arm. A timeout preserves produced files but is not a PASS.

The user approval was for this planned representative comparison; resource ceilings above are implementation bounds chosen for that task, not a claim that the user specified those numbers. No production replacement settings will be called verified before the results are reviewed.
