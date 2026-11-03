# Retained draws and diagnostic records

Part A updated the portable handoff through accepted Layer 7 and was committed
at `fb3b4f28b81605172eb9eeb2abbf321c4a1fa2f8`. Layer 8 is the accepted, implemented and validated canonical retained-draw
and diagnostic layer. It stores inference state and diagnostics, not restart checkpoints.
Layers 1-7 numerical code, fixtures, tolerances and environments remain unchanged.
No scientific run, K, chain count, cadence, run length or platform is selected.

## Bounded recovery

F is `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code`.
C is the recorded consolidation `source_snapshot/code`. The
[source inventory](LAYER8_SOURCES.csv) gives exact paths, sizes, hashes and read
ranges; the [source-to-port map](LAYER8_SOURCE_MAP.csv) records the bounded
semantic mappings and source-fragment/port hashes. All selected sources were authenticated before inspection; none was
imported or executed. There was no additional filesystem search or HPC access.

The selected F/C driver SHA-256 remains
`eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`.
`PRODUCTION_CODE_MANIFEST.json` explicitly identifies the retention-only addition
of phi/delta/tau and physical warps, plus separate checkpoint readaptation.
`PRODUCTION_RETENTION_CONTRACT.json` and `BSFM_ANALYSIS_ROADMAP.md` document
planned consumers. Their K25/four-chain/run-length choices are historical claims,
not canonical defaults. The roadmap's description of sigma2 as gene/cell-type
variance is contradicted by the implemented gene-specific variance shared across
types; the canonical model governs.
Its description of positions/permutation as sufficient to resume is also
incomplete: exact continuation requires the separate Layer-7 RNG, tuning and
complete checkpoint contract. Layer 8 does not revive that historical omission.

Verified source behavior:

- Driver 1034-1045 and 1401-1422 retain **16 fields**, including sweep. Canonical
  `loading` maps explicitly to historical `Lambda`; no scientific field is dropped.
- Driver 1395-1400 excludes settling, then retains sweep 1, cadence multiples and
  the declared final sweep. The cadence uses the local sweep index, not an offset
  from settling. Layer 8 preserves that predicate with explicit caller inputs;
  Layer 7's continued sweep numbering survives restart rather than resetting.
- Driver 1423-1435 rewrites accumulated CSV/NPZ outputs, without atomic protection
  for posterior draws. Lists are reinitialized at 1034 on restart: prior draw
  archives are not automatically merged. These are historical omissions, not
  approved crash-safety behavior.
- Driver 1271-1355 records factor visitation, block acceptance/divergences,
  integration steps, physical-W error, PCG bounds, PX checks and scalar summaries.
  Real-data permutation is identity (1317-1321), distinct from random visitation.
  Historical `divergences_total` is cumulative across visited factors/sweeps
  (1056,1224,1332), counting a split transition with either divergent block once.
  Canonical raw block counts are explicitly separate, so two divergent blocks
  are not confused with two complete factor transitions.
- `full_split.py:14,43-51` exposes all split diagnostics. Legacy `energy` and
  padded momentum describe the field block only; block energies belong to
  different conditional Hamiltonians. They must not be added or treated as a
  common stationary Hamiltonian for BFMI.
- Driver 1470-1693 distinguishes divergence review from fidelity warnings;
  `numerical_diagnostics_status` is retained before the final warning-status
  override. No historical certificate proves scientific convergence.
- Optional feedback helpers are passive instrumentation. Their block endpoints
  may be incoherent posterior states; their hard-coded detail/cadence rules are
  not imported. No between-block endpoint is a retained draw here.

## Retained fields and consumers

All arrays use explicit immutable target/input/mesh/rule identities. Native
factor order never changes when visitation order changes. The target binds cell,
gene and type axes, source rows, coordinate chart and spectral identity. Physical
coordinates remain source_native. External response/mesh/rule inputs must remain
available and authenticated; this archive does not duplicate them or raw data.

| Historical / canonical field | Shape and purpose / consumer |
| --- | --- |
| Lambda / loading | C x G x K float64; type-specific loading, fitted expression, B=alpha*Lambda |
| eta | K x N float64; fitted expression and sampled latent paint at modeled cells |
| alpha, zeta | K float64; separate scale and smooth/nugget allocation; covariance reconstruction |
| ell_eta | K float64, fixed .14; frozen feature law and labeled exact-SE reference |
| ell_U, sigma_U | K float64; legacy names for direct-W ell_W/sigma_W, not an additive displacement |
| sigma2 | G float64; shared-across-types gene noise; observable covariance and predictive noise |
| phi | G x K float64; local shrinkage diagnostics |
| delta, tau | K float64; cumulative multiplicative shrinkage / effective-rank analyses |
| W_active | K x A x 2 float64; physical active-vertex warp for interpolation/integration |
| W_cell | K x N x 2 float64; cell warp, spatial kernel/covariance diagnostics |
| positions | K x (4+2A) float64; complete sampled chart, including log-r and zW |
| permutation | K int64, identity; explicit native labels, no inferred truth alignment |
| sweep | scalar int64; continued one-based complete-sweep index |

`validate_retained_draw.py:26-34,116-166,168-231` is the directly recorded
reconstruction consumer: shapes, projector, chart parameters, cumulative tau,
fitted expression and arbitrary covariance entries. Its exact-SE covariance
check is a separate diagnostic, not the frozen finite-feature likelihood.
Keeping W, Lambda, alpha, zeta, sigma2 and the authenticated rule supports both
interpretations without claiming they agree. Layer 8 reconstructs the accepted
finite-feature inputs and fitted Y; it does not implement covariance analysis,
off-cell conditional prediction, integration, factor alignment or visualization.
No inactive outer-vertex realization is silently manufactured.

## Diagnostics and raw aggregation

Every submitted complete sweep receives a record, including nonretained and
settling sweeps. The full draw payload appears only when the caller's explicit
retention predicate is true. Retained indices are one-based and contiguous;
nonretained records have null retained index. Production count is
max(0, sweep - settling_sweeps). No production loop or save cadence is chosen.

| Diagnostic | Preserved meaning / source |
| --- | --- |
| factor_order and factor IDs | Actual Layer-6 visitation, separate from native identity permutation |
| all SplitInfo fields | Combined acceptance/divergence/step counts plus separate field/hyper values, field energy/momentum, separate energies, physical-W error |
| three full PCG diagnostic records | Iterations, relative/absolute residuals, certified posterior-metric bound, requested tolerance, convergence and conditioning diagnostics |
| complete PX audit | Before/after alpha, invariant errors, prior-draw and preservation flags |
| warp summaries and transition/eta audits | Native factor binding, target/context/position identities and coupled warp parameters |
| full Layer-6 audit | Before/after state, position and RNG hashes; fitted Y identity; no restart RNG payload |
| caller events | Explicit warning/failure code and message; never transformed into PASS |
| elapsed_seconds | Optional caller-measured monotonic complete-sweep duration excluding archive I/O; null means not measured |

All available accepted-kernel diagnostics are retained, including a nonfinite
energy on a divergent block. Typed arrays use base64 bytes/dtype/shape/hash;
nonfinite Python floats use explicit tags, never illegal JSON NaN/Infinity.
No nonfinite posterior state is allowed. A failed sweep has no SweepResult;
`record_failure` preserves a caller-supplied failure and explicitly partial
diagnostics, never a retained state or successful sweep. Failure is terminal
for that archive; there is no automatic numerical retry.

Historical truth metrics, step-size trace columns, per-block feedback,
before/after physical-W movement and TQFF fidelity/extreme-lag probes are not
returned by accepted Layer 6. They
are not reconstructed from unrelated values or relabeled successful. The fidelity
status is explicitly `not_evaluated_by_layers_1_to_8`. No monitoring kernel is
added or changed. Historical fidelity thresholds are not adopted as convergence
criteria. Numerical failure tolerances remain those of the accepted layers.

`aggregate_archives` validates inputs, sorts chains by explicit ID and returns
raw per-chain rows, split acceptance, divergence counts, separate conditional
energies, PCG iterations/error maxima, PX maxima and warning/failure events.
It rejects duplicate chains or changed target/software/run identities. Chain
ordering does not alter output. It does not pool factor-coordinate posteriors,
align factors, estimate ESS/R-hat or declare convergence: selected F/C evidence
did not establish a promoted multi-chain estimator or scientific threshold.
These remain future analysis/run-spec choices. `valid_prefix` means storage
integrity only; there is deliberately no production COMPLETE/PASS certificate.

Each aggregate energy row explicitly declares `block_order: ["field", "hyper"]`.
Its `block_energy` is a two-element semantic list built from the decoded
SplitInfo values, not the archive's base64 array descriptor. Finite entries are
JSON numbers. A divergent nonfinite entry uses the existing canonical tag
`{"_nonfinite": "inf"}`, `{"_nonfinite": "-inf"}` or `{"_nonfinite": "nan"}`;
`retained_diagnostics.decode` restores its meaning. No entry is omitted or
replaced with null. Serialization uses strict JSON without nonfinite literals.

### Independent review correction

The initial Layer-8 proposal incorrectly returned serialized `_array` descriptors
as aggregate block energies, despite documenting semantic values. Independent
review reproduced this narrow aggregation-boundary bug. The correction reads
the already-decoded `info.block_energy`, converts its two scalars to the explicit
field/hyper list and applies the existing nonfinite codec. Retained records and
their serialized diagnostics are unchanged, as are checkpoint/archive continuity,
all 16 retained fields, numerical kernels, tolerances, cadence and identities.

The original tests checked nonfinite retention but did not inspect aggregate
energy values. New tests compare both finite values exactly with direct
SplitInfo output, test positive infinity, negative infinity and NaN in either
divergent block, reject exposure of a storage descriptor at this boundary and
verify strict JSON and deterministic logical hashes. The existing reversed
chain/filesystem-order test continues to compare the complete aggregate.
The validation receipt preserves this review finding and prior test results;
the ignored review evidence also retains the complete pre-correction proposal.

## Storage and resume contract

The [versioned schema](../../config/sampler/retained-v1.schema.json) accompanies
the implementation in [retained_contract.py](../../src/bsfm/sampler/retained_contract.py),
[retained_records.py](../../src/bsfm/sampler/retained_records.py),
[retained_diagnostics.py](../../src/bsfm/sampler/retained_diagnostics.py) and
[retained_archive.py](../../src/bsfm/sampler/retained_archive.py).

Caller supplies a target, fixed b_sigma2, explicit software-contract hash, exact
Git/clean-tree/config/environment declaration, chain ID and retention policy.
The accepted Layer-7 contract builder authenticates the common continuation
identity. Layer 8 never discovers Git or an environment. Review tests correctly
declare uncommitted code; future production requires the committed clean-tree gate.

An archive has immutable `contract.json` and `records/000000000001/record.npz`,
etc. Each record contains non-object arrays and scalar canonical JSON metadata.
It binds contract, prior record hash, sweep/production/retained indices, status,
diagnostics, exact array descriptors and its own logical hash. All reads use
allow_pickle=False; unknown/missing arrays, shapes/dtypes, identities, hashes,
incoherent charts, corrupted warps and chronology fail.

A new record is written inside a unique `.attempt-*` directory under records,
flushed/fsynced/closed, independently loaded/validated, then the directory is
renamed atomically to its one numbered destination. An existing nonempty record
directory is never replaced. Failed attempts remain and are reported; they are
never consumed as successful records. Initial contract construction also uses
closed-file readback before publication. Incomplete initialization is rejected.

The supported case is a single cooperating writer on a local filesystem with
same-filesystem atomic directory rename. This is not a backup, concurrent-run
coordinator or power-loss/remote-filesystem durability guarantee. Validation
cannot detect deletion of an entire trailing suffix without an external expected
endpoint. `require_resume_boundary` therefore validates the full prefix against
the explicit Layer-7 checkpoint progress and endpoint identities. Ahead/behind
or different-state checkpoints fail; no archive trimming, duplicate replay,
merging or index skipping occurs. Failed numerical records require a separate
future recovery decision; archive I/O failure can be reopened at the last valid
prefix without discarding its failed attempt.

Normal append is one record at a time. Opening or explicitly validating an
archive reads each record independently; it does not concatenate posterior
matrices. Retained-array reads return copies. Logical content, not compressed
ZIP bytes, is deterministic. Path/attempt names do not enter logical identities.
Checkpoints remain immutable and separate; no Layer-7 API or format is modified.

## Validation and limitations

The [validation receipt](LAYER8_VALIDATION.json),
[continuation receipt](LAYER8_CONTINUATION.json), and focused tests record the
completed bounded gates. Tests compare direct Layer-6 diagnostics and exact
posterior state, independent interrupted/restarted archives, failed writes and
promotion, corruption, identity/order rejection, visible warning/divergence,
multi-chain ordering and explicit variable-cadence storage. No scientific
threshold is inferred from those synthetic tests.

Windows CPU only in the unchanged accepted Layer-5 environment. No production
runner, warmup/readaptation controller, CLI, launcher, HPC/GPU validation,
scientific fit, posterior visualization or alternative sampler is implemented.
This layer does not certify a complete downstream scientific analysis.
Exact recomputed physical-warp checks are validated in that same environment;
cross-platform numerical reconstruction has not been certified or given a new
tolerance. Caller-supplied timing is an explicit input: different measured
durations intentionally change record identities, rather than being discarded
to force deterministic hashes.
