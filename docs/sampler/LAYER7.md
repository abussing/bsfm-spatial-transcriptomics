# Complete atomic checkpoint and restart

Baseline: `164b0b1a6475805ebce3f0026f0ff58bd50f18c3`, the handoff-only
checkpoint following accepted Layer 6 at `ee84e09f9d8351744e3d6d641873974cd4b8d339`.
Layer 7 is the **accepted, implemented and validated canonical checkpoint/restart layer**.
It saves and validates
complete coherent sweep boundaries, then returns fresh restart objects. It is
exact chain continuation, not posterior-draw storage or a production runner.
Validation is bounded synthetic Windows CPU only; no scientific fit, K, chain
count, run length, save cadence or platform/GPU choice is made.

## Recovered behavior and conservative changes

Selected source:
`D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler\restart_state.py`,
6,593 bytes, SHA-256
`943a934c35a862bbc8b2d7dd80bc81ea98987e8ef10d9e7cfb152d485094b111`.
The full file was authenticated before reading. No historical imports, driver or
legacy conversion were executed. The [source map](LAYER7_SOURCE_MAP.csv) records
bounded line ranges and fragment/file hashes.

| Source | Selected behavior | Canonical treatment |
| --- | --- | --- |
| 9–10, 37–56 | State fields and validation | Complete Layer-1 state, ordered direct-W positions and both tuning blocks; reuse canonical exact chart/domain checks |
| 59–73 | External target/data/mesh contract | Explicit authenticated caller software/run contract plus complete canonical target/input/geometry/rule/spectral identities |
| 76–95 | State, tuning, RNG and spectral payload | Preserve all continuation state without object arrays; strict versioned schema and logical array hashes |
| 96–98 | Temporary NPZ followed by os.replace | Unique attempt in destination directory; flush/fsync/close; independent load validation before replacement |
| 101–119 | Contract-checked load | Reject incompatible keys/dtypes/shapes/domains/hashes and mismatched target/chart; return new objects |
| 122–126 | Restore explicit Generators and global RandomState | Restore fresh Generators only; return validated global state for explicit caller installation |

`load_legacy` (13–34) is excluded. Incomplete checkpoints, prior posterior-draw
archives, missing shrinkage/RNG state and old schema migration are unsupported.
Historical loose `allclose` checks and Python assertions are replaced by the
accepted canonical identity/domain/chart contracts. No numerical kernel,
chronology, update, RNG draw, tolerance or tuning default changes.

The historical duplicate ell_eta/ell_U/sigma_U arrays are represented completely
by the fixed ell_eta rule and complete direct-W chart. Their current summaries
are derived with accepted Layer-6 arithmetic. No transient NUTS momentum,
gradient or prepared context is persisted: accepted transitions initialize those
from the current physical/chart state on each call. Frozen field/hyper step sizes
and diagonal inverse masses are persisted; ordinary restart repeats no warmup.

## API and trust boundary

- [checkpoint_contract.py](../../src/bsfm/sampler/checkpoint_contract.py):
  `build_checkpoint_contract(target, b_sigma2=..., software=..., expected_software_sha256=...)`.
- [checkpoint.py](../../src/bsfm/sampler/checkpoint.py):
  `save_checkpoint_atomic(path, target=..., contract=..., result=..., tuning=...,
  eta_rng=..., gauge_rng=..., b_sigma2=..., progress=...)` and
  `load_checkpoint(path, target=..., contract=...)`.
- [checkpoint_rng.py](../../src/bsfm/sampler/checkpoint_rng.py): strict lossless
  JSON/RNG codecs and validation of fresh local RNG objects.

The caller supplies a Git commit, explicit clean-tree Boolean, frozen run-config
hash, environment-lock hash, environment identity and an independently expected
software-contract hash. This layer never invokes Git, discovers environments or
infers authority from directory names. These are authenticated expectations
provided by a future runner, **not independent attestation of a commit or machine**.
The accepted synthetic gate records the handoff baseline and `clean_tree=false`,
because it ran against the then-uncommitted proposal. Checkpoints preserve this
clean-tree declaration. The future production runner must require a clean,
committed tree before launch; this test does not certify that runner.

The contract also binds exact target/input/geometry/rule JSON, factor order,
spectral identity, b_sigma2 identity, fixed sharing .20, ell_eta .14, three inner
subcycles, noise-prior shape 2, chronology schema and the Layer-6 source hash.
It is strict: changed code/configuration/environment identities require a new
explicit contract, not an implicit migration or tolerance.

Save requires a completed `SweepResult`. It checks current state, positions,
fitted-value hash and all four live RNG endpoints against that result's audit.
Drawing again or mutating state before saving is rejected. The immutable target
must still validate. The API cannot prove an adversarial caller actually executed
a sweep; it enforces coherent boundary data and authenticated expectations.

Load returns `RestartState`: fresh GaussianState, ordered FieldPositions and
SplitTuning, distinct fresh eta/gauge Generators, validated NumPy global state,
JAX key, b_sigma2, progress, contract, boundary audit and logical checkpoint hash.
It does **not** install the global state. The caller explicitly executes:

```python
restart = load_checkpoint(path, target=target, contract=expected_contract)
np.random.set_state(restart.numpy_global_state)
# Then supply restart.state/positions/tuning/RNGs/key to the accepted sweep API.
```

No caller RNG or target is mutated on success or failure. Temporary local RNGs
are used only to validate and reconstruct state; they are seeded deterministically
before restoration and consume no process-global randomness or entropy. The five
explicitly supported NumPy bit-generator classes are PCG64, PCG64DXSM, MT19937,
Philox and SFC64; arbitrary class names/imports are rejected. Complete cached-normal
fields of global MT19937 are retained. JAX scalar threefry2x32 keys preserve both
key data and legacy-versus-typed representation. No stream is reseeded for a
continuation. Installing global RNG remains a caller-controlled process action.

## Versioned NPZ schema

The [metadata schema](../../config/sampler/checkpoint-v1.schema.json) documents
`bsfm.complete-checkpoint.v1`; the loader enforces the additional target-dependent
array shapes and exact semantic checks. Every NPZ member is a non-object array.
Metadata is a scalar Unicode canonical JSON string; duplicate JSON keys and
nonfinite JSON numbers are rejected. All loads use `allow_pickle=False`.

| NPZ fields | Dtype and shape |
| --- | --- |
| loading; eta | float64 [C,G,K]; [K,N] |
| alpha, zeta, delta, tau | float64 [K] |
| sigma2; phi | float64 [G]; [G,K] |
| positions | float64 [K,4+2*A], canonical factor order |
| factor_ids | fixed-width Unicode [K], exact ordered target IDs |
| field_steps, hyper_steps; inverse_mass | float64 [K]; [K,4+2*A] |
| b_sigma2 | float64 [G], exact supplied initialization scale |
| master_key; numpy_global_keys | uint32 [2]; uint32 [624] |
| spectral_U, spectral_projected_modes | exact full chart [V,V], [N,V] |
| spectral_modal_diagonals, spectral_log_modal_diagonals | exact [7,V] |
| spectral_log_coefficients, spectral_powers | exact [7] |
| spectral_log_kappa_constant, spectral_log_trace_mass, spectral_log_reference_variance | exact float64 scalar |
| metadata | scalar Unicode JSON |

The full spectral audit is retained in metadata. Every spectral member must
exactly match the supplied authenticated target, including dtype and shape; the
loader never replaces/recomputes target geometry from checkpoint data. Structural
`-inf` for log(0) is permitted only in authenticated log-modal diagonals. NaN,
positive infinity and other nonfinite spectral values are rejected.

Metadata contains exactly schema, contract, contract_sha256, progress, boundary,
position_bindings, tuning_bindings, rng, spectral_audit, arrays and logical_sha256.
Every payload array has a descriptor with dtype, shape, logical hash and Fortran
storage-order flag. Logical array hashes use the accepted shape/dtype/value encoding.
The checkpoint logical hash covers canonical metadata before adding that hash,
including every array descriptor. The returned file SHA-256 separately identifies
NPZ serialization bytes. These hashes detect integrity changes; they are not
cryptographic signatures against an actor who can rewrite all records.

Unknown, missing or duplicate archive members, incompatible metadata/schema
fields, object arrays, wrong identity/order, changed scale or state, invalid
tuning, malformed RNG records and noncoherent progress fail. Native RNG setters
are followed by exact state roundtrip checks so ignored extra/coerced fields do
not silently pass. All returned state arrays are independent copies; position
and tuning arrays are read-only as in the accepted boundaries.

Progress contains nonnegative integer `completed_local_sweep`, `settling_sweeps`
and `completed_production_sweeps`; the local count must be positive and production
count equals `max(0, local-settling)`. Local sweep count continues across ordinary
restart rather than resetting. Status is exactly `completed_sweep`, type exactly
`complete`. Settling length is caller-declared, not chosen by this layer.

## Atomicity and failure behavior

The destination parent must already exist. A uniquely named temporary attempt is
opened there, written, flushed, fsynced and closed. The normal independent loader
validates that completed file before `os.replace`. A valid existing checkpoint
is untouched by write, validation or replacement failures before promotion.
Failed temporary attempts remain at the exact path reported by
`CheckpointWriteError`, with the underlying exception chained. No automatic retry
or cleanup hides the evidence. Successful promotion consumes the temporary name.

This is same-filesystem replacement atomicity, not backup, retention, filesystem
durability against power loss, or remote-filesystem certification. In particular,
there is no directory-fsync portability claim. Concurrent writers/threads and
save cadence belong to a later runner; the historical global RNG already prevents
safe parallel chains in one process.

## Validation and stopping point

The [continuation receipt](LAYER7_CONTINUATION.json) and
[validation record](LAYER7_VALIDATION.json) distinguish actual sweep execution
from small synthetic I/O fixtures. The load-bearing test independently runs:
uninterrupted sweeps 1–2; identical fresh initialization and sweep 1; atomic save;
load into fresh objects; explicit global RNG installation; restarted sweep 2.
Comparison covers all Gaussian arrays, positions, tuning, visitation order,
fitted Y, PCG/PX/transition diagnostics, warp summaries, keys, all RNG endpoints
and complete Layer-6 audit identities. No tolerance is used for continuation.

Failure tests simulate interrupted writes and replacement errors, corrupted or
truncated archives, changed values, identities, provenance, scale, progress,
RNG and schema fields, plus object payloads. They verify preservation of an
existing valid file, failed-attempt reporting, no caller mutation, no aliasing,
and deterministic logical content. ZIP byte identity is not required.

The unchanged accepted [Layer-5 CPU environment](../../environment/sampler-layer5/README.md)
is used. No dependencies are installed. Tests run with CPU/x64 and one numerical
library thread, using the documented Layer-6 unittest command with
`-p 'test_sampler*.py'`. The eight canonical October-26 mesh tests also run.

No readaptation controller, warmup orchestration, retained posterior archives,
trace CSV, diagnostic aggregation, save cadence, production completion manifest,
CLI/batch launcher, GPU/HPC execution or legacy checkpoint conversion is added.
Frozen-tuning restart is the only implemented continuation mode. No scientific
fit or production run is supplied by this accepted layer.
