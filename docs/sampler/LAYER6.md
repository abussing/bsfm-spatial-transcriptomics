# Canonical complete Gibbs sweep

Baseline: `22b2150ec4313c65e5440cc318f56df8e6df0a36`, the handoff-only
checkpoint following accepted Layer 5 at `053092dbb713b748573b0106c08c3f6da559e33b`.
Layer 6 is the **accepted, implemented and validated canonical layer** for one complete sweep,
composing accepted Layers 1–5. It is not a production sampler, warmup controller,
checkpoint/restart system, retained-draw workflow, launcher, mixing study or fit.
Validation is Windows CPU only. K, chain count and run lengths remain unselected.

## Selected chronology and composition

Selected F source:
`D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler\run_c3full_fixed_profile_nuts.py`,
94,890 bytes, SHA-256
`eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`.
The whole file was authenticated before bounded inspection/reference execution.
The [13-entry chronology map](LAYER6_SOURCE_MAP.csv) records original line ranges,
fragment hashes, corresponding port ranges and the port-file hash. This is a
composition map, not a claim that the new orchestration has an identical AST.

The orchestration is [layer6.py](../../src/bsfm/sampler/layer6.py). The shared
[chart helper](../../src/bsfm/sampler/chart.py) and narrow Layer-4/5 host-boundary
changes allow public composition. No numerical kernel, monolith, historical
wrapper or alternative update is copied or rewritten.

| Stage | Historical source lines | Canonical composition |
| --- | --- | --- |
| Frozen constants | 41–51 | N_INNER=3, sharing .20; accepted Layer-1 phi 1.5/1.5 and delta 2.1/1.5 |
| Initialization noise scale | 494–496 | Caller supplies b_sigma2; freeze a copy and its identity |
| Three Lambda updates | 1121–1125 | Layer-1 joint type-specific loading draw |
| Features and joint eta | 1127–1143 | Rebuild every factor feature in order; Layer-4 PCG |
| Fitted Y and noise | 1145–1146 | Layer-1 fitted values, then sigma2 with shape 2.0 and supplied b_sigma2 |
| qgk / phi | 1150–1154 | Layer-1 quadratic and ordinary phi branch |
| delta / tau | 1156–1162 | Layer-1 sequential delta and cumulative tau; no fixed-precision branch |
| PX / positions / fitted Y | 1164–1172 | Accepted gauge refresh; set every log-alpha coordinate; fitted Y |
| Factor visitation | 1179–1181 | Global NumPy permutation, preserving factor labels |
| Context / key | 1182–1188 | Latest leave-factor-out statistics, then master/step key split |
| Split transition | 1189–1200 | Layer-5 field/hyper NUTS, fixed-W rewhitening and checks |
| State and warp parameters | 1201–1216 | Source operation order for alpha/zeta and coupled range/amplitude |
| One eta_k and fitted Y | 1263–1270 | Layer-3 draw immediately followed by fitted values |

There is no eta draw between field and hyper blocks and no joint eta draw after
the factor loop. Recomputed features are not cached across conjugate subcycles.
The next factor context uses the preceding factor's new eta. The source's
persistent monitoring, containment/fidelity reports, cumulative diagnostics and
capture callbacks are outside this layer. Per-transition diagnostics are returned
without suppression, retries or production aggregation.

`b_sigma2` is an explicit constructor input, copied read-only and hashed against
the bound response. The sweep never estimates or replaces it. Accepted Layer 1
still checks it against `.25*np.var(Y, axis=1)`; that comparison is validation,
not a new noise-prior estimate or update. No alternative scale/shape is selected.
Observation weights remain one; sharing and the fixed ell_eta=.14 rule remain
unchanged. All numerical draws use the accepted implementations and tolerances.

## State, chart and identity boundary

`GibbsSweep(target, b_sigma2=...).sweep(...)` requires explicit state, ordered
positions, one frozen tuning per factor, eta/gauge Generators, JAX master key,
factor IDs and an audit label. It validates response and cell/gene/type identities,
geometry/chart, rule, factor order, prior scale, positions and tuning before any
random draw. It copies the caller's GaussianState and positions and returns new
state only after all updates and endpoint checks pass. Y and caller-owned arrays
are never changed. No response centering or re-scaling is introduced.

One integration issue was recovered: the existing standalone Layer-4/5 host
wrappers demand exact inverse log/exp and logit/sigmoid equality. Even the accepted
Layer-5 endpoint fixture fails that inverse round trip:

| Quantity | Stored coordinate | Inverse of historical forward update |
| --- | ---: | ---: |
| log-alpha | 0.0718650353211414 | 0.07186503532114143 |
| logit-zeta | -0.3056439647107255 | -0.3056439647107256 |

Changing the endpoint to force an inverse match would alter the selected
chronology. One shared `validate_chart_state` helper now accepts **exact equality
in either recorded direction**, separately for alpha and zeta: the stored chart
equals log(alpha)/logit(zeta), or the state equals the historical forward
exp/JAX-sigmoid update. PX independently refreshes log-alpha while retaining
logit-zeta, so their recording conventions can differ. There is no tolerance,
clipping or rewriting. Finite/domain and complete identity checks remain.

Layer-4 `JointEtaConditional`, Layer-5 `SplitTransition`, and Layer-6 validation
all use this single helper. Layer 6 calls **public `JointEtaConditional.draw`**
for each of the three joint draws; Layer 4 owns feature, identity, RNG, immutable
state, finite-value and unchanged PCG 1e-10/80-iteration checks. Layer 6 does not
call the raw PCG kernel.

Layer 5 exposes `prepare_context(position, state, state_factor_ids=...)` and an
optional `prepared_context` argument on its public `transition` method. Layer 6
prepares the context, then splits the master key, then calls that public
transition. Ordinary direct calls prepare a fresh context themselves. Public
`validate_inputs` supplies preflight checks without context construction or RNG.
There are no Layer-6 calls to `_runner`, `_kernels`, `_result` or private split
validation methods.

A frozen, process-local `PreparedContext` contains immutable-byte-backed u/ct,
penalty, canonical context JSON and the complete position hash. Its issuing
SplitTransition registers the exact object and content signature in a weak-key
registry. An arbitrary constructor, dataclass replacement or foreign issuer
cannot authenticate it. Consumption checks the original signature, target and
factor identities, **all eight state-array hashes**, position hash, u/ct hashes
and penalty. Changed contents, positions, states and stale records fail before
transition. Records can be reused only while their exact bound inputs are
unchanged; they are not serialized checkpoints or persisted caches. Holding a
context does not grant permission to advance or mutate the Gaussian state.

The public boundaries consume the real accepted Layer-5 forward-rounded endpoint
without an inverse-roundtrip failure. Regression coverage includes one-ULP
physical-state mismatches, both recording conventions, direct/prepared equality, tampering,
foreign issuance, every state-array change and **two consecutive actual synthetic
sweeps** with all four streams continued. The original Layer-6 fixture remains
byte-identical; no expected result is regenerated to accommodate this revision.

Exact-forward equality cannot reject every one-bit chart change: exp/sigmoid
can map adjacent float64 chart values to the same physical value. For the initial
fixture, the nearest inconsistent chart changes in the tested directions are
three ULPs for log-alpha and two for logit-zeta; those are rejected. Values inside
that exact rounding plateau are accepted without a tolerance. Prepared contexts
still reject **any** changed position hash, including a one-ULP change inside a
plateau. The first focused run exposed this overly strong test assertion; the
test was corrected to the specified exact rule, with no implementation change.

The Layer-3 single-eta API deterministically rebuilds its context after alpha/zeta
are updated. These coordinates do not enter u/ct; Layer 6 requires exact matching
statistic hashes before returning the completed sweep. Its extra deterministic
recomputation consumes no RNG and the literal comparison proves unchanged draws.
Warp summaries preserve factor order and the source's arithmetic for ell_W and
sigma_W; the latter is the coupled ell_W*r_W/sqrt(10), not a new amplitude draw.

## RNG and failure semantics

| Stream | Consumers, in exact sweep order |
| --- | --- |
| NumPy global | Three Lambda/noise pairs, phi, sequential delta, permutation |
| Explicit eta Generator | Three joint-eta draws, then one single-eta draw per visited factor |
| Separate gauge Generator | One PX refresh |
| Explicit JAX master key | For each visited factor: `master_key, step_key = jax.random.split(master_key)`; accepted split kernel owns the field/hyper split |

The two Generators must have distinct bit-generator objects; aliases are rejected.
The caller selects and owns their states. The module never seeds, substitutes or
rolls back a stream. Before/after hashes include the full global RNG state
(including its cached normal), Generator state, and exact JAX key data. Hashes
audit consumption; they are not a serialized restart/checkpoint format.

Invalid inputs fail before consumption. PCG nonconvergence, nonfinite values,
failed PX or physical-W invariants, and identity failures are fatal. No partial
SweepResult is returned, but RNGs may have advanced. Transactional recovery
belongs to a later checkpoint layer. The global RNG prevents safe concurrent
chains in one process; no parallel-chain API is claimed.

`SweepResult` contains the coherent GaussianState, positions in unchanged factor
order, final key, visitation order, three PCG diagnostics, PX audit, per-factor
transition/eta-context records, ordered warp summaries, fitted Y and identities.
Divergences remain visible in the original transition info; no retry is attempted.

## Independent chronology regression

[sampler_layer6_support.py](../../tests/sampler_layer6_support.py) authenticates
the selected driver and compiles only explicitly selected AST statements from
the cited chronology. It retains the original loops, random calls, key splitting,
parameter updates and single-factor draw. Ordinary shrinkage is selected instead
of the excluded fixed-loading-precision branch. It invokes previously validated
numerical helpers but does not invoke the new GibbsSweep orchestration. No
historical imports/main routine or unrelated sampler branch is executed.

The [fixture builder](../../tests/build_sampler_layer6_fixture.py) compares that
literal reference with the canonical composition under identical initial states
and four RNG inputs. The small [saved fixture](../../tests/fixtures/sampler_layer6.json)
contains synthetic G=2/N=3/C=3/K=2 values only, plus exact logical hashes for all
transition-state/diagnostic leaves. Routine tests require no historical drive.
K=2 and the initial .01 step sizes are mechanical test inputs, not production
factor-count or tuning decisions.

The [synthetic receipt](LAYER6_SYNTHETIC_SWEEP.json) and
[validation record](LAYER6_VALIDATION.json) report actual results. The complete
state, positions, visitation order, fitted values, PCG/PX/transition diagnostics
and every RNG endpoint match the literal chronology **exactly**. Same-process and
fresh-process checks do not claim cross-platform bit identity.

The instrumented test separately proves exact call counts/order, that each next
factor sees the preceding new eta, no hidden eta draw, frozen noise-scale use,
global permutation semantics and exact master-key splits. It independently checks
PX B=alpha*Lambda, eta/alpha, actual type-block fitted Y and alpha²*q invariants
against the unchanged 5e-13 bound. Other tests cover finite/domain/order checks,
input/mesh/rule replacement, stale prepared context, tuning, caller immutability, visible
divergence, fatal failure without retry and RNG advancement on failure.

## Environment and stopping point

Use the unchanged accepted [Layer-5 CPU environment](../../environment/sampler-layer5/README.md).
Its runtime, complete package set, wheels, isolation and environment receipt are
rechecked; no package installation or environment modification occurs.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:JAX_PLATFORMS = 'cpu'
$env:JAX_ENABLE_X64 = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-cpu-20261102\python\Scripts\python.exe'
& $py -B -W error::ResourceWarning -m unittest discover -s tests -p 'test_sampler*.py' -v
```

Explicit reference acquisition uses `tests/build_sampler_layer6_fixture.py` with
the selected F `--source-root` and `--output tests/fixtures/sampler_layer6.json`.
No S10, real-data sweep, scientific warmup, mixing study, GPU/HPC execution,
checkpoint/restart, retained draws, save cadence, completion manifest, launcher,
truth alignment or LI/Fisher branch is implemented or executed here. A complete
production sampler and platform validation remain future work. No unresolved
numerical blocker has been found in the bounded comparison. The shared chart
contract and authenticated public prepared-context boundary are accepted.

The synthetic receipt preserves its original review-time status and numerical
results. Acceptance is recorded here and in the Layer-6 validation record.
