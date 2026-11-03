# GPU accumulation correction

The user authorized this correction and saved-state GPU checks after the two
diagnostics identified inherited repeated-index scatter nondeterminism.
`field_kernels.build_base_target` now selects a fixed-incidence gather/reduction
when the bound target uses the GPU default backend. The CPU path is unchanged.
Construct targets in their intended runtime; changing device/backend after
construction is not supported. No likelihood, derivative formula, prior, RNG
chronology, tuning schedule or tolerance changes.

The new helper groups contributions in original cell/corner order, masks padded
slots, and sums each vertex without conflicting writes. Memory scales with
active vertices times maximum incidence. Reduction order may differ across
compiler/hardware versions; this is not a cross-platform bitwise promise.

The Layer-3 source map retains original historical source identities and updates
only port locations/hashes and the explicit accumulation amendment. Historical
fixtures and their tolerances are not changed.

`validate_accumulation.sbatch` is the committed bounded first gate: one V100,
four CPUs, 16 GiB, 15 minutes maximum; ten fixed-input gradients and three
same-key first-factor transitions on saved real K12/L14 input. No adaptation,
scientific fit, existing-output modification or checkpoint migration. The old
software contract authenticates source input only; the gate records new code.
Success requires exact full-gradient and transition repeatability, not merely
operator agreement. Full-sweep/restart and storage timing remain subsequent
gates; success here alone cannot authorize a reproducibility claim for those.

First gate job 22015917 at `8dbff5863d2b3e2f58411180354b006bed243082`
passed: ten full-gradient evaluations exact; same-runner and new-runner
split transitions exact; autodiff relative gradient error 2.1764643911194787e-13.
Local independent dense-Gaussian and incidence tests both passed.

The next committed gate, `validate_real_replay.sbatch`, uses one V100, four CPUs,
16 GiB and at most 45 minutes. It executes three strict and three incremental
sweeps in separate processes, then interrupts sweep 2 after writing its checkpoint
candidate (before its retained record) and resumes in another process. Exact
transaction identities and completed-run non-replay are required. There is no
warmup. A diagnostic controller explicitly seeds a new software contract from
the authenticated old adapted state; the source identity is in the configuration
digest. This is an isolated diagnostic experiment, not scientific chain migration.
Wall times include compilation and validation; three sweeps do not establish
long-history scaling. No existing scientific run is modified.
