# Gaussian, shrinkage and PX layer

Baseline: `662509a9432fbb65ac0542ef4b8b2c749b796f11`.
This is the accepted, validated canonical first sampler layer of the
[selected architecture](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
It is not a complete Gibbs sampler or a production run capability.
No K, chain count or run length is selected by the synthetic test dimensions.

## Implementation and boundaries

| Module | Contents |
| --- | --- |
| [contracts.py](../../src/bsfm/sampler/contracts.py) | Frozen selected prior constants; float64/shape/domain checks; explicit input-axis identities; GaussianState bound to that input |
| [conjugate.py](../../src/bsfm/sampler/conjugate.py) | compute_Yhat, sample_Lambda_twostage, sample_sigma2_twostage |
| [shrinkage.py](../../src/bsfm/sampler/shrinkage.py) | compute_qgk, sample_phi, sample_delta_tau |
| [px.py](../../src/bsfm/sampler/px.py) | refresh_alpha_gauge and the historical invariant checks |

Only the six selected monolith functions and one selected driver function were
extracted. No whole historical module is imported. Mathematical bodies preserve
expression/loop order, array order and random calls. Validation runs before RNG
consumption and does not cast or reorder valid float64 inputs. Historical INLA
docstrings were replaced because they do not describe this selected Gaussian path.

The [source map](LAYER1_SOURCE_MAP.csv) records seven function mappings, source
files/hashes/line ranges, normalized source-fragment hashes, mathematical-body
AST hashes and port locations. The tests compare port mathematical ASTs against
those authenticated fingerprints after excluding only new contract calls and
docstrings. PX additionally rejects nonfinite outputs. The original 5e-13 PX
relative invariant threshold is unchanged.

The only default amendment is sample_delta_tau's later-delta shape: **1.5**,
matching the selected driver's explicit override. The unselected helper default
3.1 is rejected. Other selected prior settings are enforced: sharing .20,
phi shape/rate 1.5/1.5, first-delta shape 2.1, log-alpha mean log(.7) and variance
.7, noise shape 2 and fixed scale .25*population_variance(Y). Observation weights
must be one. Zero noise-prior scale is rejected rather than silently floored.
No general nonunit-weight or alternative-prior path is claimed.

Conjugate/shrinkage draws still use NumPy's global np.random stream, including
its existing gamma and standard_normal calls. PX still uses the supplied NumPy
Generator. Neither interface was replaced or reseeded inside a canonical function.
This preserves the historical two-stream behavior; it is not a thread-safe
parallel-chain API. RNG restoration/checkpointing is outside this layer.

## Input and state identity contract

Input fields are exactly Y[G,N], slocs[N,2], cell_id[N], cell_names[N],
source_row_indices[N], gene_names[G] and cell_type_names[C]. Unique ordered
Unicode IDs, unique nonnegative integer source rows, finite float64 Y/coordinates,
nonempty contiguous type blocks and increasing source rows within each type are
required. Cell identity retains both original cell ID and raw row identity.

`input_identity` records schema `bsfm.sampler-input.v1`, section,
final_centered_Y response designation, response artifact SHA-256, ordered array
hashes, axis order center_y/center_x and an explicit coordinate-system declaration.
The accepted declarations are source_native and october26_glial_min_max_span;
the latter records normalized units. No verified-micron claim, coordinate transform,
preprocessing, centering or data loading occurs here. The numerical identity
encoding matches the existing GPINIT logical hash: shape/dtype header plus ordered
little-endian numeric bytes, or JSON UTF-8 strings.

`ModelInput.authenticate(data, expected)` compares all values/axes against an
independently supplied expected identity, copies the arrays and marks them
read-only. `validate()` detects subsequent deliberate mutation. The expected
identity is a trust input: this API does not independently hash an external
response file, attest its centering, authenticate a mesh transform or establish
raw-source provenance. Future bundle adapters must supply those authenticated
expectations. No production bundle adapter is implemented in this step.

`GaussianState` contains loading, eta, alpha, zeta, sigma2, phi, delta and tau,
plus the input identity JSON. Validation requires an explicit positive integer
factor count, correct shapes, finite values, positive scales/shrinkage,
0<zeta<1 and exact tau=cumprod(delta). It does not pretend to contain W, zW,
spectral state, tuning, RNG state or a complete restart checkpoint. K remains a
caller argument, not a universal model choice.

## Bounded historical regression

The [fixture acquisition tool](../../tests/build_sampler_layer1_fixture.py)
requires an explicit selected-source root. Before any reference evaluation it
authenticates both full source hashes and the seven function line ranges.
It compiles only those function AST nodes and the two PX constants from driver
lines 43/45. No historical module imports, main routine, sampler run, GPU code
or experimental branch is executed. The reference namespace contains only
NumPy and SciPy cho_solve/solve_triangular. Reference constants come from the
selected source, independently of the port.

Three small deterministic synthetic cases cover C=1/K=1, C=3/K=2 and C=3/K=4,
unequal type populations and C/Fortran array layouts. The
[38,720-byte fixture](../../tests/fixtures/sampler_layer1.json) contains synthetic
inputs, reference outputs, both post-call RNG identities and runtime provenance;
no real observations or fitted models are included. Routine tests require no
historical drive and execute no historical source. Fixture generation is explicit.

All reference/port comparisons passed **exactly** for fitted values, qgk, Lambda,
sigma2, phi, delta/tau, PX arrays/audit and both post-call RNG states. The entire
fixture was independently reproduced with source-derived PX constants without
changing any expected values. No tolerance was relaxed and no RNG-interface
difference was encountered. This is same-environment source/port equivalence,
not a claim of identical historical Linux results across BLAS/platforms.

The 27 [focused tests](../../tests/test_sampler_layer1.py) pass, covering exact
draws and repeatability, independent qgk/PX invariants, mutation/identity/order
rejection, malformed shapes/domains/priors, RNG preservation on invalid input,
and a deliberately broken PX quadratic that must fail.

| PX invariant | Maximum measured relative discrepancy across fixtures |
| --- | ---: |
| B=alpha*Lambda | 1.891182492927259e-16 |
| eta/alpha | 1.2029458919979233e-16 |
| Signal (historical all-type einsum check) | 1.8274050374131552e-16 |
| alpha^2*qgk | 2.1977033051595429e-16 |

Independent actual type-block fitted-value reconstruction is also checked
against the unchanged 5e-13 bound. Exact source/port equality and numerical PX
invariance are distinct checks; PX involves floating-point rescaling.

## Environment and commands

No environment was installed or changed. The accepted GPINIT CPU environment
already supplies Python 3.12.0, NumPy 2.1.3 and SciPy 1.14.1. The bounded
dependency closure is NumPy plus SciPy cho_solve/solve_triangular. PX also needs
compute_qgk and the two authenticated driver constants. No newly discovered
scientific helper or missing dependency blocks this layer.

The optional sampler-layer1 dependency group records NumPy/SciPy pins only.
The validation harness additionally uses already installed threadpoolctl to fix
one numerical-library thread. This does not select a full JAX/GPU environment.
The fixture records platform and BLAS libraries; one-thread execution is a
bounded regression setting, not a selected production resource policy.

Executed from repository root in PowerShell:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$py = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\gpinit-20261102\python\Scripts\python.exe'
& $py -B tests/build_sampler_layer1_fixture.py `
  --source-root 'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler' `
  --output tests/fixtures/sampler_layer1.json
& $py -B -W error::ResourceWarning -m unittest discover -s tests -p test_sampler_layer1.py -v
```

No direct-W target, spectral marginalization, joint eta solver, NUTS, checkpoint,
launcher, GPU environment, real-data fit or HPC work is implemented or run here.
Existing preprocessing, mesh and GPINIT implementations are unchanged.
