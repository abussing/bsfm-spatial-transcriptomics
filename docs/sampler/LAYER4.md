# Fixed-physical-W conditional and joint-eta PCG

Implementation baseline: `7d18eaeade6046367cb65588a98ab99199cf8108`, the completed
storage-gate documentation checkpoint. Layer 4 is the accepted, implemented and
validated canonical fixed-physical-W conditional/rewhitening and joint-eta PCG
layer, validated on Windows CPU. It adds the two remaining non-BlackJAX numerical kernels
of the [selected architecture](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
It is not a complete sampler, hyperparameter transition, adaptation, sweep,
checkpoint/restart implementation, production launcher, GPU capability or fit.
No factor count or run length is selected. Shared durable storage remains an
operational gap, not a blocker for these local bounded numerical checks.

## Bounded source selection and port

Both complete source files were authenticated against the exact selected F
records in [the recovery ledger](../recovery/BSFM_SAMPLER_SOURCES.csv) before
any reference evaluation. No driver or historical module was imported.

| F sampler source | Bytes | SHA-256 | Ported source lines |
| --- | ---: | --- | --- |
| centered_hyper_target_qr.py | 3354 | `4bdd57d688652bf4dffb85a9c9dee1879229a7bff5c72ff34902e216226fdf5e` | 13–93 |
| joint_eta_pcg.py | 12136 | `fad132d5d171c7e7db965915b41508227521225b6397be77d747555e1aa7f74c` | 25–262 |

The [source map](LAYER4_SOURCE_MAP.csv) records 12 exact mathematical-body AST
matches, source/fragment/file hashes and line ranges. The joint-eta source's
optional dense reference at lines 265–296 is not ported; the tests construct an
independent observation-space Gaussian reference instead. Source imports that
mutate JAX global configuration are omitted; the validated boundary requires
x64 through the existing Layer-3 contract. Numerical bodies, decorators, RNG
calls, operation order, priors and solver settings are unchanged.

| Module | Responsibility |
| --- | --- |
| [centered_hyper_kernels.py](../../src/bsfm/sampler/centered_hyper_kernels.py) | Selected positive QR, contractions, fixed-W density/gradient and inverse chart |
| [joint_eta_kernels.py](../../src/bsfm/sampler/joint_eta_kernels.py) | Selected cell statistics, precision operator, block preconditioner, precision noise, PCG, nugget draw and diagnostics |
| [layer4.py](../../src/bsfm/sampler/layer4.py) | Input/state/geometry/rule/factor binding, finite/domain checks, fixed numerical contract and immutable-return boundary |

The accepted [Layer-6 integration revision](LAYER6.md) supplies a shared exact
chart/state check for `JointEtaConditional`. Its numerical kernels, PCG settings
and accepted fixtures are unchanged. The original Layer-4 validation receipt
preserves the host-file hash tested at that checkpoint; the Layer-6 validation
receipt records the revised host-file hash and regression results.

The only centered-kernel helper is the already authenticated Layer-2
`spectral_modal_geometry`. Layer-3 `DirectWTarget` supplies the frozen ordered
1024-column features for each factor; no second feature implementation is
introduced. Neither a target monolith nor any LI/Fisher, containment, soft-eta,
precision-experiment or historical-generator branch is imported.

## Fixed-physical-W target

Let `x=log(ell_W)`, `b=log(r_W)`, `n` be the active-vertex count, and
`L(x)L(x).T=Sigma_A(x)` the full-spectrum raw-Q marginal covariance. The two
coordinate columns share L and `sigma=exp(x+b-.5*log(10))`. For fixed physical
`W[n,2]`, define `Z=solve(L,W)/sigma`. In the dx db measure, ignoring constants:

```text
log p(x,b | W) = -2*n*log(sigma) - 2*sum(log(diag(L)))
                - .5*sum(Z*Z) - .5*x*x/.25 - .5*b*b/.09
```

Both determinant terms include the two coordinate columns. There is no factor
likelihood, loading penalty, range-dependent variance normalization, clipping,
jitter, omitted mode, or extra lognormal Jacobian. Independent priors remain
`x ~ N(0,.5^2)` and `b ~ N(0,.3^2)`.

The selected ordinary positive-diagonal QR computes the log-range contractions
without differentiating a noncentered field. For Q from the thin QR, modal
log-SD derivative a, `T=sum(a*row_sum(Q^2))`, `U=sum(a*(Q@Z)^2)`, and
`S=sum(Z^2)`, the gradient is `[-2*n-2*T+S+U-x/.25, -2*n+S-b/.09]`.
The historical custom JVP also retains the W derivative. This conditional must
not replace the noncentered Layer-3 field target.

`CenteredHyperTarget.freeze` creates a read-only, hashed physical-field record
from an authenticated position. `value_grad` validates that record and the
current model/state/factor binding but never evaluates a likelihood.
`rewhiten` returns `solve(L_new,W)*exp(-x_new-b_new+.5*log(10))` using the exact
source operation order, checking physical-W reconstruction against the inherited
`2e-8` limit. It does not accept/reject or update hyperparameters or state.

## Joint eta conditional and numerical contract

The solver temporarily uses scaled loadings `Lambda*alpha` and normalized latent
fields eta/alpha. Neither input is overwritten. With `D=diag(sqrt(1-zeta))`,
cell loading precision U and score r, it constructs
`H=(I+U*D^2)^-1 U`, symmetrizes floating-point H as in the source, and computes
`s=(I+U*D^2)^-1 r`. Smooth features are `F_k=sqrt(zeta_k)*Phi_k`.

```text
Q_beta = I + F.T blockdiag(H_i) F
rhs_mean = F.T s
rhs_noise = epsilon_beta + F.T blockdiag(H_i^1/2) epsilon_cell
beta = PCG(Q_beta, rhs_mean + rhs_noise)
```

The preconditioner is block diagonal in factors, with each full feature block
`I + F_k.T diag(H_kk) F_k` Cholesky factored once per draw. No dense fallback or
partial factor update is provided. Conditional nugget draws follow the beta
solve, in canonical cell order, and the final output returns to eta coordinates
by multiplying by alpha. All factors are updated jointly.

The exact NumPy Generator order is: `(K,R)` prior innovations, `(N,K)` coupling
innovations, then one K-vector per cell for the nugget. There is no JAX random
key or implicit reseeding in the public API. Nonconvergence raises before any
eta result is returned; RNG consumption up to that failure is retained as in
the source. GaussianState is never updated by these methods. Invalid identity
or state inputs are rejected before consuming RNG.

The public contract fixes the maximum at **80 PCG iterations** and the reported
posterior-Mahalanobis RMS beta-solve bound at **1e-10**. For Q >= I,
`e.T Q e = residual.T Q^-1 residual <= ||residual||^2`, so the historical bound
is `||residual||/sqrt(K*R)`. It uses the recursive PCG residual, unchanged from
the source. This is a floating-point numerical approximation with a checked
bound, not an exact Gaussian draw or a rounding-error interval certificate.
Small dense tests independently evaluate the actual solution error and residual
relation. No solver threshold was relaxed.

One historical numerical detail is explicit: precision-noise construction
rejects `min(eig(H)) < -2e-10`, then clamps remaining negative roundoff
eigenvalues to zero before square roots (source 142–144). That inherited
PSD safeguard is preserved exactly; it is not added covariance jitter or a new
fallback. Its measured minimum and H asymmetry are retained in diagnostics.

## Identity and API boundaries

Both public kernels bind to the entire Layer-3 target identity: authenticated
Layer-1 input/state identities, ordered cells/genes/type mappings, Layer-2
geometry/chart, frozen rule and ordered factor IDs. Changed geometry, arrays,
rule or factor order are rejected, even when dimensions agree. Joint eta
requires one position per ordered factor and exact matching current-state
log-alpha/logit-zeta chart coordinates. It builds every feature matrix through
the canonical Layer-3 implementation. Current state, positions, features and
RNG states are identified in returned audit metadata.

The low-level numerical modules are trusted algebra, not artifact loaders.
Host hashing/validation is not proposed as an inner-NUTS-loop design. These
kernels do not load production bundles, authenticate an independently supplied
external identity by themselves, or implement a complete sampler state.

## Validation and environment

The unchanged accepted [Layer-2 CPU environment](../../environment/sampler-layer2/README.md)
is reused: Python 3.12.0, JAX/JAXlib 0.7.0, NumPy 2.1.3, SciPy 1.14.1,
ml_dtypes 0.6.0, opt_einsum 3.4.0 and threadpoolctl 3.5.0. No installation or
environment change occurred. This does not establish GPU or Linux validation.

The [fixture builder](../../tests/build_sampler_layer4_fixture.py) authenticates
both source hashes before executing only the 12 selected AST definitions.
Two [saved synthetic fixtures](../../tests/fixtures/sampler_layer4.json) compare
fixed-W values, hand and AD gradients, physical fields, inverse charts, joint
eta/beta, all diagnostics and final RNG states **exactly** in this environment.
Ordinary tests use those fixtures without accessing legacy paths. Canonical
1024-column beta arrays are represented by complete ordered logical hashes;
tiny four-column beta arrays are stored explicitly. No cross-platform bit
equality claim or sign/order alignment is used.

The [24 focused tests](../../tests/test_sampler_layer4.py) include independent
full-precision/active-covariance density and AD gradients, determinant
multiplicity, priors, likelihood independence, rewhitening, dense joint
posterior mean/covariance, full innovation-map covariance, precision products,
preconditioner blocks, posterior-metric error, forced nonconvergence, malformed
input and identity rejection, exact source fingerprints, state immutability,
and same/fresh-process determinism.

Initial reference-test failures are retained in [the validation record](LAYER4_VALIDATION.json):
the new tests incorrectly asked PCG to match dense beta/eta at a generic `2e-12`
elementwise threshold (observed maxima about `4.33e-12` and `1.43e-11`), and
asked separately assembled right-hand sides to yield bit-identical diagnostics.
Those are not the historical numerical promises. The corrected tests retain
the exact source/port gate, test the approved posterior-metric bound directly,
and verify eta-error propagation through the independently assembled linear
conditional map. The existing `2e-12` algebraic comparison budget is retained
for that propagation and dense reference roundoff. No kernel, fixture,
scientific setting or PCG tolerance was changed to pass these tests.

Final suites passed **99 sampler/provenance tests plus eight canonical mesh
tests**, including R/fmesher integration, with no skips. Unrelated SCT/GPINIT
suites were not rerun. Maximum measured independent discrepancies across the
two small systems were:

| Check | Maximum |
| --- | ---: |
| Fixed-W density relative error | 5.879e-15 |
| Fixed-W independent AD gradient relative error | 5.286e-15 |
| Dense joint posterior mean / covariance absolute error | 8.327e-17 / 4.441e-16 |
| Actual beta posterior-metric RMS error | 1.143e-11 |
| Corresponding reported PCG bound | 1.256e-11 |
| Eta-error propagation discrepancy | 2.944e-16 |

Dense-solve beta and eta are not bit-identical to a tolerance-controlled PCG
draw. Their maximum absolute differences were `1.924e-11` and `1.435e-11`,
respectively; exact equality applies to the historical source versus port and
same-environment repeated executions, not to those dense comparisons.

## Bounded S10 smoke

The [smoke receipt](LAYER4_S10_SMOKE.json) hashes the existing canonical artifact
and all used arrays before constructing a synthetic G=2/K=2 state. It reads no
expression data and generates no mesh. Cell IDs explicitly alias raw source
rows because original cell-name strings are absent from that handoff.

| Measurement | Result |
| --- | ---: |
| Cells; MIC / AST / OGC | 9,422; 996 / 3,337 / 5,089 |
| Full vertices / modes / active vertices | 371 / 371 / 168 |
| Features / eta / beta | 2 x 9,422 x 1,024 / 2 x 9,422 / 2 x 1,024 |
| PCG iterations, both runs | 10 |
| Reported posterior-metric RMS bound | 5.1517393144791e-13 |
| Physical-W rewhitening maximum error | 5.551115123125783e-17 |
| First centered / joint draw | 2.489 / 3.004 seconds |
| Repeated centered / joint draw | 0.960 / 2.325 seconds |
| Total smoke runtime | 10.998 seconds |
| Peak process resident working set | 983,420,928 bytes |
| Exact repeated outputs, diagnostics and RNG / unchanged state | pass / pass |

Memory includes Python/JAX/native libraries; no child workers were used. The
smoke is a mechanical check, not mixing, posterior convergence, scientific
accuracy, factor-count selection, or an all-section resource estimate.

## Reproduction commands and remaining scope

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:JAX_PLATFORMS = 'cpu'
$env:JAX_ENABLE_X64 = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer2-cpu-20261102\python\Scripts\python.exe'
& $py -B -W error::ResourceWarning -m unittest discover -s tests -p 'test_sampler*.py' -v
& $py -B tests/audit_sampler_layer4_s10.py `
  --mesh-artifact 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_october26_S10_angle_fix_20261102\sampler-facing.npz' `
  --output artifacts/review/sampler_layer4/s10-smoke.json
```

Explicit fixture acquisition uses `tests/build_sampler_layer4_fixture.py` with
`--source-root` set to the selected F sampler directory and `--output` set to
`tests/fixtures/sampler_layer4.json`; it also generates the source map. Ordinary
tests do not regenerate expectations. Large logs and the full proposed patch
stay in ignored review storage. No BlackJAX NUTS, adaptation, factor/sweep
chronology, checkpoint/restart, retained draws, launcher, GPU environment or HPC
execution is included. No bounded dependency is missing; full sampler correctness
and later transition integration remain unestablished. This bounded Layer-4
implementation and validation are accepted; K and production run lengths remain
unresolved. No HPC workflow, mixing study or scientific fit is established.
