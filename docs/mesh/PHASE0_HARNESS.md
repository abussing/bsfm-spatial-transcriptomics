# Experimental Phase-0 harness — approved for Phase 0 only

This harness implements the [approved study](../../config/mesh/study-design.json)
and [scientific design](../decisions/ADAPTIVE_MESH_DESIGN.md) using new canonical
source in [src/bsfm/mesh](../../src/bsfm/mesh). It is **not a selected production
mesh**. Only synthetic inputs have been used. No S10 candidate, GP initialization,
sampler, historical builder or HPC job has run in this implementation gate.

The [synthetic report](audits/phase0_synthetic_20261102/README.md) distinguishes
mechanical checks from continuum accuracy. Numerical tolerances and the precise
mesher/probe mapping are approved for the Phase-0 experiment only in
[phase0-harness.json](../../config/mesh/phase0-harness.json). They do not change
the frozen scientific target or make the 2% trial targets acceptance thresholds.
The **21-degree minimum angle and all other mechanical settings are approved
for Phase 0 but remain provisional for production**. Independent review approved
the harness, not a production mesh implementation. Real S10 execution still
requires separate authorization against the exact committed harness.

## Modules and authentication

| Module | Responsibility |
| --- | --- |
| inputs, identities | Authenticate clean generating commit, config, immutable environment, receipt, section manifest, whole response file and coordinate/identity axes before scientific use. |
| coordinates, support | Preserve center_y/center_x and source_native units; subtract all-cell component minima and divide by 6532.1214803230505; convex support, collar and connected enclosure. |
| bridge, fmesher_bridge.R | Isolated R 4.5.3/fmesher 0.7.0 geometry and projector only; deterministic graded construction and independent achieved-edge checks. |
| geometry, projectors | Zero-based geometry; positive triangles, topology, region labels; independent P1 projection without a nearest-triangle fallback. |
| fem, spectral | Independent consistent P1 mass/stiffness and complete generalized eigensystem. |
| continuum, marginal, derivatives, accuracy | Unit-variance continuum reference, full covariance, exact active block, positive-diagonal root, derivatives, finite differences and separate continuum discrepancies. |
| probes | Fixed 256 geometry-only probes and separate gap diagnostics. |
| resources | Parent plus recursive-child RSS monitoring and termination; durable failure records. |
| artifacts, phase0 | Closed-file validation, unique attempts, atomic promotion, sequential six-candidate pilot. |

The real CLI rejects a dirty working tree or wrong expected commit. It checks
the immutable mesh environment tree, shared R runtime tree and runtime/package
locks. The receipt and external v2 run manifest must both hash to
`03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f`.
The registered section manifest then authenticates the complete response HDF5
file. Cell IDs, raw rows, mapping, types and coordinate-axis identities are read
and hashed before coordinate arrays. Expected counts, float64 coordinates,
source-row uniqueness, MIC/AST/OGC block order and exact joins are checked.
No response-expression dataset is opened. Hashing the response file necessarily
streams its bytes, but does not deserialize expression arrays.

Real runs retain the approved six geometries and 23 ranges each. Study/config
and clean source identities are checked again between candidates. Synthetic
tests explicitly use a separate fixture and cannot substitute factors through
the real CLI. The current design still records execution_authorized=false:
the command below needs separate user approval and a reviewed committed harness.

## Exact Phase-0 grading translation

Let H be the convex hull of **all eligible cells**, c the frozen fine-collar
width and b the candidate buffer measured outward from the collar. The connected
domain has no hole boundaries, including between separated point clusters.
The collar approximates H plus a radius-c disk; the outer boundary approximates
H plus a radius-(c+b) disk. Both polygons are intersections of support halfplanes
at all hull-edge normals and 128 uniformly spaced angles. Vertices are ordered
deterministically. This is a circumscribed polygon approximation, not an exact
circular offset: the conservative radial excess bound is
`(c+b) * (sec(pi/128)-1)`. It is reported in every geometry record.

At every supplied boundary/location point, quality.spec receives
`min(h_inner + 0.15*d, ell_high/4)`, with Euclidean distance d outward from the
collar polygon and d=0 inside. Initial locations are the support vertices,
collar vertices and all-cell centroid, sorted and deduplicated. Observation
positions are projected afterward; they are not compulsory mesh vertices.

The pinned fmesher implementation supports sampled per-vertex quality values.
Its refinement code interpolates their logarithms; this is **not** an analytic
callback for the requested distance function. Evidence is the authenticated
maintainer archive `fmesher_0.7.0.tar.gz`, SHA-256
`6a1c4e69c5d2a235edcc3a613cb0cff0015ceee78b65c2d342bc05e12ff8a185`:
`R/mesh_2d.R` lines 176–203, 317–319, 479–493 and `src/meshc.cc`
lines 656–658, 772–774. The archive is in the external environment source cache;
no package source was copied into this repository.

Consequently each returned edge is independently tested using the **minimum
distance along the entire edge** to the collar, not just its midpoint. Its length
must be no larger than the target there, up to relative tolerance 1e-8. Because
the target is nondecreasing in distance, this is a conservative whole-edge upper
size constraint. Violating edges contribute midpoint seeds; all prior vertices
are retained as location inputs in the next round, and fmesher reconstructs the
triangles. Seeds are lexicographically sorted and unique. Eight rounds is the
fixed limit; exhaustion fails the candidate without changing h, b or grading.

The mapping certifies an **upper edge-length constraint**, not equality to the
target, an optimal vertex count, or exact continuous-field interpolation inside
fmesher. Its dense polygon boundary can over-refine synthetic enclosures. Eight
achieved-distance bins report min/median/max edge lengths and maximum target
ratio. Minimum angle 21 degrees, disk topology, positive area, one component,
enclosure membership and independent R/Python projectors must also pass. The
cutoff is 1e-12 in numerical coordinates. These mechanical choices, including
the unchanged 21-degree minimum angle, are approved for Phase 0 and remain
provisional for production; no geometry has been selected on accuracy.

## FEM, covariance and derivatives

For each triangle of area a, the local mass is
`a/12 * (ones(3,3) + I)` and stiffness is
`a * grad(phi) @ grad(phi).T`. No lumping or boundary-value constraints are
introduced. Thus the discrete weak operator has natural Neumann boundary
behavior. The complete generalized eigensystem satisfies
`G U = M U Lambda`, `U.T M U = I`; all n modes, including the constant mode,
are retained. Roundoff-negative eigenvalues may be clamped only within the
explicit eigensystem tolerance; material negativity fails.

For nu=5, kappa=sqrt(40)/ell, the modal variance and its log-range derivative are

```text
w_i = 20*pi/kappa^2 * (1 + lambda_i/kappa^2)^(-6)
dw_i/dlog(ell) = w_i * (2 - 12*r_i/(1+r_i)), r_i=lambda_i/kappa^2
Sigma_full = U diag(w) U.T
Sigma_active = U[active,:] diag(w) U[active,:].T
```

This is the project application of the SPDE Matérn normalization, with
`tau^2=1/(20*pi*kappa^10)` in two dimensions; see
[Lindgren, Rue and Lindström (2011)](https://doi.org/10.1111/j.1467-9868.2011.00777.x).
The independent small-matrix test uses dense inverses and matrix powers:
`20*pi*kappa^10 * (K^-1 M)^5 K^-1`, `K=G+kappa^2 M`.
No sampler amplitude or post-hoc diagonal rescaling enters either calculation.

Active vertices are exactly the nonzero columns of the observation projector,
independent of geometric support/collar/buffer labels. Inactive vertices are
marginalized by selecting the active covariance block of the full-domain model,
not by solving a smaller boundary-value problem. QR of the transposed weighted
active eigenvectors constructs a lower-triangular root L with positive diagonal.
For `D=dSigma_active/dlog(ell)`, set `X=L^-1 D L^-T`, retain the lower triangle
with half its diagonal as Phi, then `dL=L Phi`. Tests check both covariance-root
identities and centered finite differences at steps 1e-3, 1e-4 and 1e-5.

The analytic reference is `z^5 K_5(z)/384`, z=kappa*distance, with value 1 at
zero, a small-z series below 1e-3 and exponentially scaled Bessel evaluation
elsewhere. An independent gamma-mixture quadrature oracle follows
[DLMF 10.32.10](https://dlmf.nist.gov/10.32.E10). Its expression is
`integral(t^4 exp(-t-z^2/(4t)), t=0..infinity)/Gamma(5)`.

Every range reports variance error, absolute covariance/correlation error,
relative covariance Frobenius error, distance bins, four strata and gap-probe
results. Correlation normalization is diagnostic only; saved covariance/root
hashes identify the unrescaled unit-amplitude calculation. Full-to-active,
projected full-to-active, root reconstruction, root derivative identity and
finite-difference errors are separate mechanical results. Passing these does
not establish continuum fidelity or certify the full continuous range interval.

## Fixed probes and ordering

All modeled cells retain the canonical bundle order. Probe candidates have
unique raw source rows even when locations coincide. Boundary score is distance
to the all-cell hull boundary; interior uses its negative. Density is distance
to the 20th other nearest neighbor (query includes self). Dense/sparse scores
are this radius and its negative. Within each score the lowest raw source row
breaks ties. Each initial pool is the best quarter of observations, at least 64.

Precedence is boundary, interior, dense, sparse, 64 each without replacement.
Selection maximizes minimum Euclidean distance from all previously selected
probes, with smallest raw row breaking ties; the first probe has the smallest
raw row in its pool. If overlap exhausts a pool, it expands to all remaining
observations. Expansion counts are recorded. Exactly the same identities and
order are supplied to all six candidates; probes are frozen before errors.

Separate gap diagnostics use endpoints of Euclidean MST edges surviving cutoffs
3, 4 and 5 times the median 20-neighbor radius (equivalently exceeding 5 times).
Duplicate positions are collapsed for this diagnostic only. A SciPy Delaunay
graph supplies candidate MST edges; it never supplies FEM mesh triangles.
This is the approved Phase-0 operational gap diagnostic, **not anatomical classification
or a claim to reproduce M3's original gap labels**. It does not replace any of
the 256 probes or alter topology. Degenerate density may produce many extra
probes; resource exclusion is preferable to silently dropping them.

## Artifact and resource protocol

New experiment roots are required. Existing failed roots are retained; automatic
resume or replacement is not implemented. Each candidate uses a unique attempt:

```text
external-experiment-root/
  run-spec.json                 # study, code, config, input identities
  inputs.npz                   # coordinate/identity transport only, outside Git
  probes.json
  .attempt-<candidate>-<uuid>/  # retained diagnostics/failure evidence
    work/bridge/round-*/        # narrow R inputs/outputs/logs
    worker.log
    validator.log
    validator-execution.json
    deep-validation.json
    failure.json               # only on failure
  <candidate>/                 # atomically promoted, exactly eight files
    run-spec.json
    geometry.h5
    probes.json
    ranges.json
    compute.json
    execution.json
    validation.json
    manifest.json
  checkpoint-01.json ... checkpoint-06.json
  manifest.json                # only after all six validate
  failure.json                 # failure instead of final success
```

[Candidate specification](../../schemas/mesh/phase0-spec.schema.json) and
[manifest schema](../../schemas/mesh/phase0-manifest.schema.json) are versioned.
`geometry.h5` preserves raw/numerical all-cell and modeled coordinates, explicit
IDs/source rows/type codes/membership, vertices/vertex IDs/zero-based triangles,
regions, hull/collar/outer polygons, full eigenpairs, active indices, CSR
projector/mass/stiffness. Numerical arrays are float64, indices int64, IDs UTF-8.
CSR groups contain data/indices/indptr, shape and explicit index_base=0.
HDF5 uses lossless gzip/shuffle for dense numeric arrays. Exact file hashes
authenticate serialization; logical hashes exclude compression and timestamps.

Mesh numerical logical hashing uses little-endian C-order bytes preceded by
sorted-key JSON `{dtype,shape}` and LF. UTF-8 IDs use uint64 little-endian byte
length prefixes, matching the canonical preprocessing ID convention. Input
numeric hashes use the preprocessing convention (bytes only); the formats are
explicitly distinct. All scientific matrix axes remain recoverable from IDs.

Before promotion, a separate fresh process reopens the closed files and checks
schemas, hashes, full identity joins, geometry/projectors, reassembled FEM,
eigenpair residuals/orthogonality, deterministic probes and full range inventory.
Both computation and deep validation are supervised. The parent verifies the
deep validator's authenticated file records, writes the final manifest and
renames the candidate directory on the same filesystem. Directory existence or
process exit alone is insufficient. Fast closure validation authenticates every
final file and the deep-validation receipt. Attempt logs are optional diagnostic
records; a copied eight-file candidate validates without the surrounding attempt.
This format is deliberately separate from six-file preprocessing bundles.

Concurrency is one. Real preflight requires 8 GiB available RAM. A 50 ms sampler
counts RSS of the parent plus all descendants, including R, and kills the worker
tree when it observes more than 10 GiB. This is a monitored ceiling, not an OS
reservation: transient overshoot between samples is possible, and summed RSS
can conservatively count shared pages more than once. Dense-algebra estimates
also reject obviously oversized candidates; they are estimates, not guarantees.
No spectrum, observation set, range set or probe count is reduced after failure.
The independent validator is subject to the same monitoring. Failed attempts
are retained with input/spec identities and the unexecuted candidate list.

## Commands for review

Synthetic tests, using the existing immutable environment:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$env:BSFM_MESH_INTEGRATION = '1'
& 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031\python\Scripts\python.exe' -B -m unittest discover -s tests -p 'test_mesh_phase0.py' -v
```

Projected six-candidate command, **not executed or authorized by this review**.
After committing the approved harness and obtaining separate execution approval,
replace the placeholder with that exact commit; use a fresh external destination:

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
$env:OMP_NUM_THREADS = '1'
$env:OPENBLAS_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
& 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031\python\Scripts\python.exe' -B -m bsfm.mesh.phase0 `
  --environment 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031' `
  --response-root 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2' `
  --expected-commit '<REVIEWED_HARNESS_COMMIT>' `
  --section 'S10__WT5' `
  --run-root 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_phase0_S10_v1' `
  --execute-phase0
```

Remaining limitations: Windows-only evidence; synthetic coverage cannot predict
S10 memory or accuracy; offset discretization/over-refinement and probe policy
are approved only for Phase 0 and remain provisional for production; physical
units remain unauthenticated; gap diagnostics are not an
anatomical classifier. There is no Phase-1 launcher, production mesh selection,
holdout implementation, sampler coupling or plotting subsystem in this harness.
