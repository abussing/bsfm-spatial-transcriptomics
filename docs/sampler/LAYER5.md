# Split BlackJAX transitions and window adaptation

## GPU provenance amendment, 2026-11-04

Main now includes the reviewed GPU-only acceptance roundoff guard from `1bb4493`.
The source map authenticates the amended full file/body; the provenance test
removes only that exact guard and verifies the remaining historical body hash.
`make_logdensity` remains body-exact. The guard only bounds overshoot through
eight float64 epsilons; all other invalid values remain invalid.

See the [current runtime scope](../WORKFLOW_GUIDE.md#runtime-interfaces-and-acceptance-scope)
for GPU execution evidence and saved-reference reconciliation. Fixtures and
tolerances are unchanged. The following baseline describes original CPU acceptance;
it does not supersede the later scoped GPU evidence.

Baseline: `68c0f2214849daf051a29db08acf55429fd246ed`, the handoff-only
checkpoint following accepted Layer 4 at `b028663b027d60e2914c70542a6d82246834a2ee`.
Layer 5 is the accepted, implemented and validated canonical split field/hyper
NUTS transition and window-adaptation layer. Validation is Windows CPU only.
It implements one factor's split transition and bounded window adaptation, not
a complete Gibbs sampler or a scientific warmup/mixing result. K, chain count and
production run lengths remain unresolved.

## Authenticated source and bounded dependency

The selected F package `code/sampler/full_split.py` is 4,705 bytes, SHA-256
`f2b26f954d49dc51dfa542874df0de87936698db7714fca907292a7c495b06cd`.
Its complete `build_split` body (lines 19–88), namedtuple declarations and imports
are preserved in [split_kernels.py](../../src/bsfm/sampler/split_kernels.py).
The required analytic-gradient bridge `make_logdensity` is extracted only from
selected driver lines 242–261 (94,890-byte driver SHA-256
`eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`).
It supplies the canonical Layer-3 value/gradient through the original custom VJP;
cotangents for fixed u, ct and penalty remain zero with their original shapes.
No driver, eta draw, alternative kernel or historical monolith is imported.

Both complete source identities are authenticated before reference evaluation.
The [source map](LAYER5_SOURCE_MAP.csv) records source/fragment/port hashes and
two exact mathematical-body AST matches. Original sources remain external.

## Exact transition and adaptation contract

For `p = [log_alpha, logit_zeta, log_ell, log_r, zW(row-major, two columns)]`:

1. Split the supplied key once as `kf, kh = jax.random.split(key)`.
2. Initialize fresh BlackJAX field state and gradient from the current caller
   state's u, ct and penalty. Jointly update indices `[0,1,4,...]`, holding `[2,3]`
   fixed, with the accepted Layer-3 direct-W likelihood and priors.
3. Freeze physical active W from that field endpoint using accepted Layer 4.
4. Initialize a new hyper state; update only `[2,3]` using the fixed-W conditional.
   This density has no factor likelihood. The two coordinate columns share its
   geometry/range/amplitude, as in Layers 2–4.
5. Rewhiten the same physical W at the new hyperparameters and rebuild the full
   endpoint density/gradient. No eta draw or state mutation occurs in this layer.

The source/driver relative invariant is
`norm(W_after-W_before) / max(norm(W_before), 1e-100) < 2e-8`.
This is recorded separately from Layer 4's standalone absolute-error check.
Nonfinite endpoints or failed relative invariants are fatal; no clipping,
jitter, fallback, silent retry or alternative acceptance rule is introduced.

Frozen mechanics: BlackJAX 1.3, target acceptance 0.9, maximum doublings 10,
initial step sizes 0.01, separate diagonal mass and step-size adaptation for the
field and hyper blocks. Adaptation requires an integer of at least 20 transitions.
The original BlackJAX `base(True, .9)` and `build_schedule(steps)` are retained.
All adaptation keys are produced by `jax.random.split(key, steps)`. The source
scans batches of 20 while carrying both the latest position and adaptation
states across batch boundaries. Field mass updates use the field endpoint before
rewhitening; hyper updates use the hyper endpoint. Both final learned step sizes
and the combined diagonal mass are returned, alongside the last warmup position.
These constants are mechanics, not a chosen scientific warmup length.

Legacy `energy` and zero-padded `momentum` describe **only the field block**.
Hyper momentum is not combined into that Hamiltonian. Block acceptance,
divergence, leapfrog count and energy remain separate, as does the W error.
Aggregate acceptance is their mean, divergence their logical OR, and leapfrogs
their sum. Divergences remain visible; the layer does not hide or automatically
retry them. The historical adaptation view records the field step size and
combined mass; final tuning separately preserves the hyper step size.

## Public boundary

The accepted [Layer-6 integration revision](LAYER6.md) supplies a shared exact
chart/state check and an authenticated `prepare_context`/`prepared_context`
interface. Ordinary calls still build a fresh context; prepared calls validate
the issuing object, contents, full state and position before consuming it. The
description below records the originally accepted direct-call interface. Its
numerical kernels, tuning and fixtures remain unchanged. Original validation
hashes identify the accepted checkpoint; the Layer-6 receipt records the amended
host boundary and regression results.

[layer5.py](../../src/bsfm/sampler/layer5.py) binds the transition to the accepted
input/state, geometry, frozen rule and ordered factor identities. Every call
validates those identities and builds a fresh `DirectWTarget.context`; it never
accepts a stale cached Yhat, gradient or conditional statistic. Initial position
alpha/zeta must match the selected factor in the supplied GaussianState.
The explicit position owns the warp chart, which GaussianState does not contain.

Tuning is factor/target bound, diagonal, positive, finite, read-only and hashed.
Returned positions are read-only. Initial tuning can be constructed explicitly;
this does not claim that it was learned. `adapt` returns frozen learned tuning,
the propagated endpoint, diagnostics and the complete bounded adaptation history.
The caller must reconcile the returned position with its later state updates;
this layer does not implement that Gibbs chronology. It consumes an explicit
scalar threefry2x32 key, returns no next key, and never advances a global RNG.
The caller owns key advancement. Both legacy uint32 keys and scalar typed keys
are accepted; batched and alternative-implementation keys are rejected.

Kernel construction caches only fixed target/geometry code. Host identity checks
are outside the JIT-compiled trajectory. Low-level kernels assume authenticated
inputs; the public boundary supplies shape/domain checks and raises on invariant
failure even if Python assertions are disabled.

## Validation and its limits

The [fixture builder](../../tests/build_sampler_layer5_fixture.py) compares
historical source and port in the new pinned CPU environment. The
[10-KiB fixture](../../tests/fixtures/sampler_layer5.json) retains exact hashes of
every state/diagnostic/history leaf, with dtype and shape, plus scalar summaries.
It includes a 100-step eight-coordinate synthetic adaptation and subsequent
transition, and one canonical Layer-3/4 small-system transition with 1,024 features.
The synthetic adaptation is a mechanical window-schedule test, not a BSFM warmup.
It recorded one divergence in each block; those remain visible mechanical
regression results, not a scientific warmup, mixing result or production tuning
claim. They are retained, not tuned away.

Exact comparison covers outputs, keys, two learned step sizes, mass blocks,
endpoints, full histories and field-only diagnostics. Same-process and fresh-
process comparisons use the same locked Windows CPU stack, not a cross-platform
bit-equality claim. Independent tests instrument the two coordinate partitions
and key order, verify the hyper density does not evaluate the likelihood,
reconstruct W from an independently executed field block, and test identity,
malformed tuning, endpoint propagation, no eta/Y/state mutation, divergence
visibility and fatal invariant failures. Existing Layer-4 independent conditional
and joint-Gaussian checks remain unchanged.

All **119 sampler/provenance tests and eight canonical mesh tests** pass with
no skips, including 20 focused Layer-5 tests and R/fmesher mesh integration.
The first focused pass had a test-harness error: it attempted to assign into
a protected mapping before exercising validation. The corrected test replaces
the record with an identity-inconsistent mapping; numerical kernels and
tolerances were unchanged. Results and file identities are in
[LAYER5_VALIDATION.json](LAYER5_VALIDATION.json). No S10 transition was run: the
canonical small-system check suffices for this accepted bounded layer. No scientific
accuracy, convergence, mixing or production performance is inferred.

## Environment and reproduction

The [separate Layer-5 CPU environment](../../environment/sampler-layer5/README.md)
extends all seven accepted Layer-2 pins with BlackJAX 1.3 and a resolved pinned
dependency closure. The accepted Layer-2 environment is not changed. Sources,
wheel hashes/sizes, offline restoration, runtime and library isolation are recorded.
This is not an authenticated CUDA/GPU or HPC production environment.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:JAX_PLATFORMS = 'cpu'
$env:JAX_ENABLE_X64 = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-cpu-20261102\python\Scripts\python.exe'
& $py -B -m unittest discover -s tests -p 'test_sampler*.py' -v
```

No conjugate subcycles, post-factor eta refresh, random factor visitation,
whole-sweep chronology, checkpoint/restart, retained draws, production diagnostic
aggregation or launcher is added. No GPU/HPC execution, factor-count or run-length
selection, LI-ESS, LI-NUTS or Fisher method is included. Large environments,
archives and complete review logs/diff remain outside Git or in ignored storage.
