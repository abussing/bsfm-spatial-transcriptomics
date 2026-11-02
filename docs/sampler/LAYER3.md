# Frozen finite-feature factor likelihood and direct-W field target

Baseline: `d76927b274bfca9e9e24032ee7db07241fbb6d00`.
Layer 3 is the accepted, implemented and validated canonical finite-feature/
direct-W factor-target layer of the
[selected architecture](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
It supplies a factor target and one conditional eta draw, not a complete Gibbs
sampler, transition, mixing test, production fit, production runner or GPU capability. K, chain
count and run lengths remain unselected. Layers 1 and 2 are unchanged.

## Source selection and bounded extraction

The [22-entry provenance map](LAYER3_SOURCE_MAP.csv) records exact F source paths,
sizes, SHA-256, line ranges, normalized source-fragment hashes, source/port AST
hashes and port-file hashes. Fifteen mapped bodies are AST-identical. The others
specialize selected branches or add an authenticated boundary; they are not
described as unchanged whole functions.

| Selected source | SHA-256 | Used ranges |
| --- | --- | --- |
| fixed_splusu_dynamic_target.py | b172a3732b30c2e15387ad898565a1c9971d902352d9bfd54485a7937295748e | selected branches of 21–409; statistics 412–431; eta draw 479–503 |
| direct_w_dynamic_target.py | 245c5e9f5ed91f511a9bf69e75a0a832b68f8a66a04d424d05dbdd3734adfd65 | selected adapter 9–55, excluding containment |
| rule_contract.py | 955ce44ef4df3a07a232fb33dd0e1310526df1dae84dc92f32bf2c768be230de | selected rule checks 3–10 |
| run_c3full_fixed_profile_nuts.py | eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49 | factor_context 233–239; argument evidence 418–439; tolerance evidence 620–662 |

The only additional bounded code dependency is the driver's seven-line
`factor_context`, which combines the selected sufficient statistics with the
already accepted Layer-1 `compute_qgk`. No driver, monolith, transition or wrapper
is imported. Source authentication uses exact paths, since the recovery inventory
contains distinct driver versions with identical basenames.

| Canonical module | Responsibility |
| --- | --- |
| [rule.py](../../src/bsfm/sampler/rule.py) | Frozen rule identity, ordering, dimensions, weights and x64 checks |
| [finite_features.py](../../src/bsfm/sampler/finite_features.py) | Exact feature, collapsed likelihood and derivative algebra |
| [factor_statistics.py](../../src/bsfm/sampler/factor_statistics.py) | Exact sufficient statistics, loading penalty and single-eta draw |
| [field_kernels.py](../../src/bsfm/sampler/field_kernels.py) | Selected live-warp/fixed-feature-range kernels and direct-W prior/chart adapter |
| [field_target.py](../../src/bsfm/sampler/field_target.py) | Validated Layer-1/Layer-2/rule/factor joins and current-state evaluation |

The specialization fixes `live_warp_hypers=True`, `live_ell_eta=False` and
containment disabled. Unreachable setup and branches are removed. No eta-floor
wrapper, soft-eta option, fixed-physical-W target, LI/Fisher machinery, alternative
rule, mode truncation or variance renormalization is ported. The original feature
helpers retain their derivative intermediate with respect to log(ell_eta), but
that variable is fixed and is neither a target coordinate nor an exposed option.

## Authenticated rule

[L16_ell14.json](../../config/sampler/L16_ell14.json) contains the ordered float64
frequency, weight and square-root-weight arrays, dimensions, feature ordering,
x64 requirement, source manifest identity and historical NPZ identity.
The F `cloud_run.py:38` reference names `rules/L16_ell14.npz`; its package
`SOURCE_MANIFEST.json` authenticates the 6,579-byte artifact:

`d2add950144186c9e7f46c36df5db75ae13538e5cd65be9b7951781c04a464e5`.

The 67,153-byte JSON registry is pinned at
`e39e1597b842b1c71698e9ee180cff3632b6f7b966f9cdaadef1ee13214812d9`.
JSON roundtrip preserves every float64 value exactly. Ordinary tests need no
historical drive. The registry retains the source table/pickle/commit identities
as historical metadata, without claiming that the original generator was rerun
or those further artifacts independently inspected. No rule generation occurs.

For ordered frequencies omega[j] and weights w[j], the cell feature row is

```text
Phi(W_i) = [sqrt(w_j)*cos(W_i dot omega_j) for j=0..511,
            sqrt(w_j)*sin(W_i dot omega_j) for j=0..511]
ell_eta = 0.14
C_eta = alpha^2 * [zeta*Phi*Phi.T + (1-zeta)*I]
```

This finite-feature covariance defines the implemented likelihood. The historical
exact-SE label is diagnostic/provenance only; it does not substitute a continuum
kernel. Frequencies are not reseeded, permuted or rescaled to another outer range.
Historical tolerances remain: weight sum 2e-14 absolute and squared square-root
weights 1e-12 relative. Array hashes reject permutations even when covariance is
mathematically invariant to the permutation.

## Conditional target and RNG contract

The current-factor residual is Y minus the other factors. For cell i of type c,

```text
u_i  = sum_g Lambda[c,g,k]^2 / sigma2[g]
ct_i = sum_g Lambda[c,g,k] * residual[g,i] / sigma2[g]
penalty = tau[k] * sum_g phi[g,k] * qgk[g,k], sharing s=0.20
d_i = 1 + alpha^2*(1-zeta)*u_i
H = I_1024 + alpha^2*zeta * Phi.T @ diag(u/d) @ Phi
rhs = sqrt(alpha^2*zeta) * Phi.T @ (ct/d)
log L = -.5*sum(log(d)) + .5*sum(alpha^2*(1-zeta)*ct^2/d)
        -sum(log(diag(chol(H)))) + .5*rhs.T @ solve(H,rhs)
```

Terms constant in this conditional block are omitted as in the source. The
log-alpha target adds C*G*log(alpha) minus alpha²*penalty/2, plus its Normal
prior with mean log(.7) and variance .7. The zeta prior including its logit
Jacobian is `2*log(zeta)+2*log(1-zeta)`. Whitened zW has the standard-normal
quadratic. Log ell_W has mean zero/variance .25; log r_W has mean zero/variance
.3². The .3² is the selected driver's explicit override of the direct helper's
unused .25 default. No separate lognormal Jacobian is added when expressing
these priors in their log-coordinate chart.

The position is `[log_alpha, logit_zeta, log_ell_W, log_r_W, zW row-major]`.
Both zW columns share the same full-spectrum active root L:

```text
sigma_W = exp(log_ell_W + log_r_W - .5*log(10))
W_active = sigma_W * L @ zW
W_cells = barycentric_gather(W_active)
```

There is no additive identity field. The original direct adapter's translate,
prior correction and chain-rule ordering are preserved rather than algebraically
simplified. The source's gather/scatter arithmetic and Layer-2 QR derivatives
are retained. Zero zW gives zero W_cells.

`sample_single_eta` retains the NumPy Generator, 1,024 beta innovations followed
by N cell innovations, Cholesky solves and original operation order. It returns
a draw; it neither changes the supplied state nor executes a Gibbs subcycle.

## Identity and state boundary

`DirectWTarget` requires authenticated `ModelInput`, `WarpGeometry`, the frozen
rule and an explicit ordered tuple of unique factor IDs. Section, coordinate
chart and axis order must agree, and coordinates, cell IDs and raw source rows
must match exactly. Gene identities are bound through the input/state identity.
The host API rejects a state or position from another binding, reordered factors,
mutated arrays, nonfinite values, malformed zW, nonpositive noise, and
unrepresentable alpha/zeta/range values. It never clips to manufacture validity.

Every target evaluation and eta draw recomputes Yhat, u, ct and the penalty from
the supplied current state. Only the geometry/rule kernels are cached. Y is not
recentered, scaled, replaced or mutated. Current state, statistics and fixed
identities are hashed in the returned context record. Alpha/zeta in a proposed
position may differ from the supplied state: they are precisely coordinates being
evaluated, not stale statistics.

As in Layers 1/2, input expected hashes must come from an independently
authenticated bundle. These objects do not themselves implement a production
response/GPINIT loader. Low-level JAX/NumPy kernels are trusted algebra called
inside that validated boundary, not independent untrusted-artifact entry points.
Host-side hashing is not a design for an eventual NUTS inner loop.

## Validation and environment

The accepted [Layer-2 CPU environment](../../environment/sampler-layer2/README.md)
is reused unchanged: Python 3.12.0, JAX/JAXlib .7.0, NumPy 2.1.3, SciPy 1.14.1,
ml_dtypes .6.0, opt_einsum 3.4.0, threadpoolctl 3.5.0, pip 23.2.1.
No dependency, environment or GPU setup was added. Its recorded runtime and
wheel hashes and installed package set were rechecked.

The [reference utility](../../tests/sampler_layer3_support.py) authenticates all
four selected source files before evaluating only named function ASTs. In the
reference factory, only the inactive containment import/construction is removed;
no substitute likelihood is injected. Other unselected reference branches are
never executed. The reference uses the already source-compared Layer-2 active
root and Layer-1 qgk helpers; it does not import their historical modules again.
The [saved fixtures](../../tests/fixtures/sampler_layer3.json)
contain two tiny synthetic systems. Every recorded target value, hand gradient,
AD reference gradient, W value, full feature hash, statistic, eta draw and
post-call RNG state matches exactly in the same CPU environment. No historical
Linux byte-equivalence claim is made and no tolerance was loosened.

The [21 focused tests](../../tests/test_sampler_layer3.py) include a separately
expressed small cell-space Gaussian integral, dense raw-Q inverse/active
Cholesky, independent JAX differentiation, posterior mean/covariance and
innovation-map comparisons, input immutability, current-state rebuilding,
same/fresh-process determinism, ordering/identity corruption and provenance.
Historical driver tolerances are retained: relative value error 2e-12 and
relative gradient norm error 2e-10, both divided by max(1, reference norm/value).
Posterior and feature identities use 2e-12. All **70 sampler tests** and
**8 canonical October-26 mesh tests**, including the R/fmesher angle boundary,
pass with no skips. Unrelated preprocessing/GPINIT suites were not rerun.
The [validation record](LAYER3_VALIDATION.json) gives measured discrepancies,
environment/check results and hashes.

## Bounded S10 mechanical smoke

[LAYER3_S10_SMOKE.json](LAYER3_S10_SMOKE.json) authenticates the existing canonical
mesh handoff and all used arrays. No mesh rebuild or expression array read occurs.
The original cell names are unavailable in that handoff, so identifiers explicitly
name raw source rows. Synthetic two-gene/two-factor Y/loading/noise data exercise
the target; this is not a factor-count decision, mixing test or scientific fit.

| Measurement | Result |
| --- | ---: |
| Full cells; MIC/AST/OGC | 9,422; 996 / 3,337 / 5,089 |
| Full vertices / retained modes / active vertices | 371 / 371 / 168 |
| Feature matrix / gradient | 9,422 × 1,024 / 340 |
| Target value | -127.62628730063994 |
| Gradient finite; exact repeated value/gradient | pass; pass |
| First evaluation / repeated evaluation | 3.311 / 0.957 seconds |
| Total smoke runtime | 6.329 seconds |
| Peak process working set | 1,048,502,272 bytes (0.977 GiB) |

Memory is the Windows process lifetime peak resident working set, including
Python/JAX/native libraries; the smoke uses no subprocess workers. It is not a
future GPU or full-sampler memory estimate. Initial smoke fixture construction
used literal tau=.88; the existing exact cumprod check rejected it before target
evaluation. The fixture now derives tau from delta. No target formula, tolerance
or scientific setting changed to pass the smoke.
The smoke was repeated after strengthening full rule-identity revalidation;
its value and all four logical output hashes were unchanged. The table and
receipt record that final source version.

## Commands and stopping point

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:JAX_PLATFORMS = 'cpu'
$env:JAX_ENABLE_X64 = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer2-cpu-20261102\python\Scripts\python.exe'
& $py -B -W error::ResourceWarning -m unittest discover -s tests -p 'test_sampler_layer*.py' -v
& $py -B tests/audit_sampler_layer3_s10.py `
  --mesh-artifact 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_october26_S10_angle_fix_20261102\sampler-facing.npz' `
  --output artifacts/review/sampler_layer3/s10-smoke.json
```

Explicit fixture acquisition uses
[build_sampler_layer3_fixture.py](../../tests/build_sampler_layer3_fixture.py)
with `--source-root` equal to the exact F sampler directory in the source map,
and `--output tests/fixtures/sampler_layer3.json`. Ordinary tests only read the
saved fixture. Full logs and the proposed patch remain in ignored review storage.

No bounded dependency is missing. Windows CPU equivalence, the small-system
independent checks and one S10 mechanical evaluation do not establish GPU
readiness or sampler correctness. Centered fixed-W targets, joint-eta PCG,
NUTS/adaptation, factor chronology, checkpoints, launchers, all-section execution
and HPC work remain outside this layer. The bounded implementation and validation
have been accepted for the separately authorized Layer-3 commit.
