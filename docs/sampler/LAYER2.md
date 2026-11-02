# Full-spectrum warp and active marginalization

Baseline: `d534788b373071f29853af2a62600b07d57e5fbe`.
Layer 2 is the accepted, implemented and validated canonical deterministic
warp/active-marginalization layer of the
[selected sampler architecture](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
It is not a complete Gibbs sampler, likelihood, stochastic transition or
production-run capability. K and run lengths remain unselected.

## Bounded implementation and provenance

| Module | Responsibility |
| --- | --- |
| [spectral.py](../../src/bsfm/sampler/spectral.py) | Full generalized eigensystem authentication, all seven modal diagonals, raw-Q law and first/second log-range derivatives |
| [active.py](../../src/bsfm/sampler/active.py) | Historical positive-diagonal QR, QR JVP derivative, exact active covariance and fixed-amplitude physical field |
| [projector_encoding.py](../../src/bsfm/sampler/projector_encoding.py) | The selected three-entry barycentric gather encoding only |
| [warp.py](../../src/bsfm/sampler/warp.py) | Frozen FEM constants, authenticated input/chart boundary, shared two-column coupling, direct cell projection and deterministic rewhitening |

The [nine-function source map](LAYER2_SOURCE_MAP.csv) records original F paths,
bytes, SHA-256, line ranges, normalized fragment hashes, mathematical AST hashes
and port locations. Mathematical bodies of those nine functions are unchanged.
The selected source identities are:

| Source | SHA-256 |
| --- | --- |
| spectral_live_range_whitening.py | d4e0d7a63c1fba65bc0410cfd04be4b695202b9babd9a8756e707a07a2b5f803 |
| active_marginal_whitening.py | 81e1a613d605edfee1da28a30a03d664959e20ca512dbfa2001776d04ce093b6 |
| splusu_active_tqff_target.py | e05c68a97db4e5d8c61001e66f3e74e8d7233a1733e0476c756aef76405a673c |
| generate_splusu_phase1.py | 7e9fb03fd484b2768775a3604296476e39423813b5b191ad9fa1c8752161169f |

Only FEM constants at lines 28-35 and the dense-reader semantics at 55-59 are
used from the last file. Only barycentric_triplets at 13-38 is extracted from
the broad target file. No gallery, generator, alternative target or monolith is
ported. [LAYER2_BOUNDARIES.json](LAYER2_BOUNDARIES.json) records these bounded
helper identities and the unchanged canonical functions reused.

The existing October-26 FEM assembly, polynomial export, Matrix Market reader,
projector construction/validation and active-support extraction are reused.
No mesh construction code is added or changed. The existing NumPy spectral/root
checks are retained as independent comparisons. The historical sampler loader
adds its exact audit/derivative contract; its QR JVP must not be replaced by the
different NumPy Cholesky-differential diagnostic. No rejected study launcher,
configuration or range grid is imported or restored.

## Preserved numerical contract

The full basis U satisfies U.T C U=I. All V full-mesh modes are retained,
including the constant mode. The seven authenticated diagonals are those of
U.T G_j U, with G_0=C. For nu=5, FEM order 6, spatial dimension 2:

```text
kappa = sqrt(40)/ell
q_m = (1/(20*pi)) * sum(j=0..6) binom(6,j)*kappa^(2-2*j)*d[j,m]
sd_m = exp(-log(q_m)/2)
B = U[active,:] * sd[None,:]
L = positive-diagonal-QR(B.T).R.T
Sigma_active = B @ B.T = Sigma_full[active,active]
sigma_W = exp(log_ell + log_r - log(sqrt(10)))
W_active = sigma_W * L @ Z                 # Z: active_vertices x 2
W_cell = A_active @ W_active
```

The two columns share geometry, range and amplitude. Direct W has no additive
reference-coordinate/displacement term. Inactive vertices are integrated out,
not conditioned to zero. There is no eigenmode truncation, jitter, added modes,
variance normalization, array permutation or reseeding. Raw variance and its
derivatives remain diagnostics only, and changing the diagnostic reference
variance does not change modal SDs.

The source returns first and second derivatives of modal SD, log precision and
log raw mass variance with respect to log(ell). The active root derivative is
computed by JAX JVP through QR itself. Historical physical_active derivatives
hold sigma fixed. The explicit coupled interface additionally returns
dW/dlog(ell) = sigma*L_r*Z + W and dW/dlog(r)=W.
Rewhitening solves L_new*Z_new=W/sigma_new, checks the reconstructed physical W,
and returns coordinates only; it performs no hyperparameter update or draw.

Historical tolerances are retained: spectral identities 2e-10, scale-aware
negative-modal authentication 2e-12, projector validation 5e-12, gather threshold
1e-13 with reconstruction limit 2e-14, and physical-W preservation 2e-8.
The negative-diagonal clamp runs only after the historical authentication check.
No tolerance was relaxed after observing results. New independent derivative
tests use the existing 2e-10 numerical identity threshold; this is not a new
scientific approximation or continuum-accuracy criterion.

## Identities and API limits

`WarpGeometry.authenticate(data, expected)` requires seven full FEM terms,
full mesh vertices, full projector, cell locations, sorted active indices,
explicit unique vertex and cell identifiers, and unique raw source rows.
All numeric geometry arrays are finite float64; index arrays are integers.
Active indices must exactly equal the full projector's nonzero support.
The canonical projector checks enforce row coverage, weights and affine identity.
The gather encoding preserves its original fail-on-reconstruction-error behavior.

The versioned identity records section, expected mesh artifact SHA-256, ordered
logical hashes for every array, zero-based indexing, center_y/center_x axis order,
the October-26 minimum/maximum-span transform designation and normalized units.
It does not authenticate physical microns. Copied arrays are read-only; validation
detects deliberate changes to input arrays or the spectral chart.

The expected identity is supplied by the caller and must come from an independently
authenticated bundle. This interface does not read a production response bundle,
prove that a declared transform was applied, or replace a sampler input adapter.
S10's audit authenticates its external artifact against the committed mesh receipt.
That mesh artifact supplies source rows, not original cell-name strings, so audit
cell identifiers explicitly name raw source rows. No names are guessed.

Host methods validate domains, identities and finite/positive outputs. Low-level
JAX functions preserve the historical differentiable signatures for use inside a
future validated target closure; callers must not treat them as independent
untrusted-input loaders. Host hashing is not proposed inside a future NUTS loop.

## Environment

The new [isolated CPU environment](../../environment/sampler-layer2/README.md)
uses JAX/JAXlib 0.7.0, NumPy 2.1.3 and SciPy 1.14.1. Python is the existing
authenticated Windows 3.12.0 runtime, rather than historical Linux 3.11.14;
the reason and exact versions, archive hashes, sizes, package constraints,
offline installation, x64, BLAS and library isolation are recorded there.
All seven package wheels are retained outside Git. No existing environment was
modified. No CUDA/BlackJAX/GPU production claim follows from this CPU validation.

## Validation and measured S10 results

The [bounded reference utility](../../tests/sampler_layer2_support.py)
authenticates the four approved source hashes and compiles only the named function
ASTs and FEM constants. It imports no historical module or driver. Two small
synthetic FEM fixtures compare all recorded arrays and diagnostics exactly with
the port in the same pinned environment. The
[saved fixture](../../tests/fixtures/sampler_layer2.json) contains synthetic values
only; ordinary tests do not require a historical drive.

The [22 focused tests](../../tests/test_sampler_layer2.py) cover generalized
eigen identities, exact polynomial precision, all modes, raw variance behavior,
root positivity/reconstruction, first/second derivatives, JIT/JVP, coupled
physical mapping, dense inverse/Schur marginalization, projector identities,
same-process and fresh-process determinism, Matrix Market roundtrip, source AST
equivalence and malformed/mutated input rejection. All 27 accepted layer-1 tests
also pass unchanged in this environment: **49/49 sampler tests**.
The eight existing October-26 mesh tests also pass in the accepted mesh
environment, including the JSON/Python/R angle-boundary regression that stops
before constructing a mesh. Total bounded validation: **57/57 tests**, no skips.
The complete unrelated preprocessing/GPINIT/R suites were not rerun for this layer.
The [validation record](LAYER2_VALIDATION.json) contains test counts, checks and
implementation/fixture hashes.

The [S10 audit](LAYER2_S10_AUDIT.json) consumes the already authenticated
7,195,273-byte canonical mesh handoff with SHA-256
`69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0`.
It does not rebuild a mesh or open expression arrays. It uses the existing
mechanical check ell=1 and one deterministic inverse-chart change to ell=.9;
there is no range study or production-selection decision.

| Measurement | Full geometry cells | Historical retained cells |
| --- | ---: | ---: |
| Cells | 9422 | 4712 |
| Full vertices / retained modes | 371 / 371 | 371 / 371 |
| Active vertices | 168 | 167 |
| Historical source versus port | exact | exact |
| Repeated execution | exact | exact |
| Full-to-active covariance relative error | 5.882e-16 | 5.896e-16 |
| Root reconstruction relative error | 9.722e-16 | 9.600e-16 |
| Root derivative identity relative error | 1.464e-15 | 1.446e-15 |
| NumPy canonical root versus JAX relative error | 1.591e-14 | 1.594e-14 |
| Projector row-sum maximum error | 2.220e-16 | 2.220e-16 |
| Projector affine maximum error | 1.110e-15 | 1.110e-15 |
| Rewhitening active/cell maximum error | 3.886e-16 | 3.886e-16 |

The bounded S10 audit took 7.22 seconds. Historical-versus-port comparisons
were exact, including U, modal diagonals, projected modes, roots, derivatives,
physical fields and gather encodings. This means the selected source and port
executed identically **in this CPU environment**, not that historical Linux
arrays were reproduced bit-for-bit. No eigenvector sign/order adjustment was
needed. The independent NumPy-versus-JAX root comparison is numerical, not exact.

Independent dense precision inversion and Schur-complement checks run on the
small synthetic FEM systems. For S10, the independent dense calculation is the
full V-by-V spectral covariance followed by its active submatrix. It does not
claim a reliable direct inverse of the ill-conditioned raw S10 precision.
S10 mesh counts are regression observations, not scientific targets.

## Commands and stopping point

From the repository root, use the new environment's Python:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:JAX_PLATFORMS = 'cpu'
$env:JAX_ENABLE_X64 = 'true'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer2-cpu-20261102\python\Scripts\python.exe'
& $py -B -W error::ResourceWarning -m unittest discover -s tests -p 'test_sampler_layer*.py' -v
& $py -B tests/audit_sampler_layer2_s10.py `
  --mesh-artifact 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_october26_S10_angle_fix_20261102\sampler-facing.npz' `
  --source-root 'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler' `
  --output artifacts/review/sampler_layer2/s10-audit.json
```

Fixture acquisition is separately explicit via
[build_sampler_layer2_fixture.py](../../tests/build_sampler_layer2_fixture.py)
with the same source root and `--output tests/fixtures/sampler_layer2.json`.
No extra scientific dependency was discovered. The remaining boundaries are
future input adapters and the as-yet unported sampler layers. Direct-W likelihood,
finite features, joint eta, NUTS/adaptation, chronology, checkpoints, launchers,
GPU environment and HPC work were neither implemented nor run. No changes are
staged, committed or pushed during the implementation-review gate; this layer
was subsequently accepted for the separately approved commit.
