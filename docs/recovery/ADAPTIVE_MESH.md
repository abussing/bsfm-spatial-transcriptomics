# Adaptive tissue mesh recovery through M2

Status: **historical recovery through M2 complete within its bounded scope; no
canonical mesh implementation or numerical design selected**. Baseline:
`1c9f36331fd55d3ddd1953199499fe084f30293f`. This checkpoint records the reviewed
M1/M2 evidence; it does not authorize implementation, a sensitivity study, mesh
generation, GP initialization or HPC execution.

The next gate is a scientific mesh design and bounded accuracy/resource study.
The October 26 four-stage fmesher implementation is the **best-supported
historical candidate**, based on inspected source, linked metadata, all-section
geometry records, authenticated numerical reports and recorded downstream
consumption. This is not a selection or a claim of scientific adequacy.

See the [evidence ledger](ADAPTIVE_MESH_EVIDENCE.md),
[evidence-strength table](ADAPTIVE_MESH_EVIDENCE.csv),
[source identities](ADAPTIVE_MESH_SOURCES.csv), and
[unresolved-decision ledger](ADAPTIVE_MESH_DECISIONS.csv).
Aliases below resolve to exact paths in the evidence ledger.

## Evidence distinctions

- **Verified source behavior**: static inspection of identified source bytes;
  not proof that those bytes executed.
- **Authenticated historical measurement**: a parsed result from an identified
  archive or certificate, not a new computation from scientific arrays.
- **Documented historical claim**: a historical note or reported approval;
  original approval transcripts were not recovered.
- **Mathematical inference**: deduction from the implemented algebra, explicitly
  distinguished from empirical evidence and a chosen scientific model.
- **Unresolved scientific choice**: requires judgment or missing evidence before
  canonical selection.

## Scientific purpose and recovered lineage

The intended adaptive mesh has finer resolution near tissue observations and
progressively coarser outward layers, retaining a buffered full latent domain.
Inactive vertices are marginalized, not fixed to zero. This intent is reflected
in the repository capability inventory, historical notes and inspected algebra.

| Stage | Evidence and change | Limitation |
| --- | --- | --- |
| September 8 tissue preview | A/AUDIT.txt:18-20 describes a two-offset fmesher mesh, S06 187 active / 394 total. | Original builder not located; later summary only. |
| September 14 graded-buffer revision | A/AUDIT.txt:21-29 says four explicit extension stages replaced an interface that honored only two layers; contours at .02/.18/.45, old far polygon retained. S06 527 active and olfactory 659 active were deliberately finer. | Original source and sensitivity document not located; numerical motivation not authenticated. |
| September 30 / October simulation work | W/build_mesh_preview.R:13-48 constructs four stages around a fixed unit square, with targets .18/.26/.38/.55 and cutoff .081 in the recorded example. W/mesh_preview_v2/INDEPENDENT_VALIDATION.json records 224 vertices. | Simulation-domain support is not a tissue-support policy. |
| October 24 tissue production | P/production/build_section_mesh.py builds a custom triangular lattice and Delaunay mesh with nearest-cell bands and refinement. | No minimum-angle acceptance gate; iteration cap can leave oversized triangles reported. |
| October 26 corrected tissue geometry | A/build_preview.R, byte-identical to F/build_preview.R, restores four explicit fmesher stages with tissue hulls, inherited far boundary, requested 25-degree angle and approximately 175 active vertices. | Computational size target is not a convergence criterion. |
| October 26 preparation and October 30 review | F exports consistent FEM operators and retained-cell projectors; C records all-19 visual approval and CPU preparation; R has matching section counts and plots. | Approval is a documentation claim. Plot-generation attestation and actual corrected-mesh sampler execution remain unrecovered. |

E, L, P, C and Z contain overlapping package/overlay lineage, not independent
solutions. CURRENT/PRODUCTION/CONSOLIDATION labels and timestamps confer no
authority. A similarly named desktop MESH_METHOD_HANDOFF_20260826 was excluded
after documentation identified an unrelated insurance/storm model.

The original September files were absent at exact tested paths under
`D:\johnston_brain`, `D:\johnston_brain\artifacts`, and
`D:\johnston_brain\run_bundles`. The inspected indexes/manifests did not resolve
them. This does not prove permanent loss or absence elsewhere. No original study
justifying inner resolution, grading distances or outer extent was recovered.

## Coordinates, support and S12

The [canonical handoff](../decisions/MODELING_RESPONSE_HANDOFF.md) preserves
`/obsm/spatial` unchanged in `[center_y, center_x]` order, units `source_native`,
with unit declaration `not_found`. M2 reused the accepted full-row axis audit;
it did not rescan all coordinate rows.

Captured review.py:71,78-79,126-130 reads raw spatial coordinates, selects section
rows by sample code and gen_fine, selects Mic/AST/OGC, and writes `xy=xy[gidx]`.
P/production/prepare_sections.py:58-76 stably orders these cells by type;
:94-99 applies the exact historical transform

```text
origin = componentwise minimum over the supplied section's glial cells
scale  = maximum of the two axis spans over those cells
z      = (source_xy - origin) / scale
source_xy = scale * z + origin
```

There is no rotation/reflection in that boundary. Historical x/y column names
do not authenticate raw anatomical orientation. Parameters .02/.18/.45 are in
normalized coordinates, not verified microns. Applying them directly to raw
source_native coordinates would change their meaning. Canonical coordinates
must remain unchanged; any future numerical coordinate transform needs a
separate explicit contract.

Bounded H5AD attribute inspection found only encoding attributes on spatial and
center_x/center_y arrays. Small spatial metadata gave `spot_diameter_fullres=50`,
`tissue_hires_scalef=0.1261805137047547`, and `use_quality=hires`; these do not
authenticate a physical unit. Associated johnston_paper.txt:300-308 states
0.108 micrometers/pixel for plaque-training image ROIs, but does not connect that
scale to this H5AD coordinate array. Historical `coordinate_scale_microns` and
HANDOFF.md's micron claim remain unverified. No conversion was inferred.

| S12 section | Recorded animal | Glial cells | Origin | Scale |
| --- | --- | ---: | --- | ---: |
| S12__Trem2_1 | Trem2_1 | 11650 | [-21.55676039173438, 46.2336321820116] | 6630.451357195608 |
| S12__Trem2_5xFAD2 | Trem2_5xFAD1 | 13485 | [5112.87625146899, 81.92749625504395] | 6417.476744719765 |

The two sections share sample and are separated by gen_fine, not an inspected
geometric component algorithm. Never infer animal identity from suffixes.
Neither inspected S12 source/preview certificate records component or hole
counts. cells.csv exists for both sections, but its generation record was not
recovered. Coordinates in those CSVs were not opened as arrays.

Historical population flow:

```text
all section cells in upstream normalization
 -> glial selection (MIC/AST/OGC)
 -> stable type ordering and coordinate normalization
 -> full-glial geometry and observation projector
 -> every-other-cell selection within type in Morton order
 -> subset projector rows, recompute active columns
 -> unchanged full mesh and full FEM operators
```

F/prepare_inputs.py:35-58,77-101 establishes the post-geometry subset. It does
not rebuild the hull after thinning. No inspected source establishes use of all
raw cell types for this tissue mesh. The current canonical response instead
retains every modeled glial cell, without thinning. Downstream covariance code
receives matrices and identities, not a biological definition of tissue support.
Support cells and observation cells must therefore be explicit separate choices.

## Adaptive settings and topology

| Property | October 24 custom builder | October 26 four-stage fmesher |
| --- | --- | --- |
| Support | Nearest-cell distance bands; observed convex-hull vertices | Nonconvex hulls of supplied glial locations |
| Bands | .07/.18/.45/1.0 | Hull padding .02/.18/.45 then inherited outer boundary |
| Edge controls | Spacing .045/.08/.14/.28; nominal edges .06/.105/.18/.35; refinement trigger 1.75 times target | Initial h=.13; edges h/max(.20,1.35h)/max(.30,1.90h)/max(.55,2.5h) |
| Adaptation | Bounded refinement; remaining violations recorded | Up to five attempts; seek 150-200 active vertices and choose closest to 175 |
| Hull controls | Custom lattice and Delaunay | concave=.12, resolution=150, eps=.006; cutoff=.45h; extend=FALSE |
| Quality | Area/projector checks; no minimum-angle gate | Requested min.angle=25; coverage, weights, area, grading and boundary checks |
| Outer extent | Custom buffered construction | Exact old boundary inherited; no independently justified new maximum extent |

Sources: P/production/build_section_mesh.py:25-33,111-215; A/build_preview.R:50-86.
The all-19 recorded inner targets range from .10720074626605919 to .13; other
targets are .20/.30/.55. Minimum cell-boundary clearance is approximately
.7556-.7575 normalized units, not a maximum outer extent.

Earlier contours become internal constraints, not holes or separate SPDE
boundaries. No explicit anatomical-hole policy or prevention of bridging
disconnected tissue was established. Buffering can change connectivity; actual
component counts were not measured here. fmesher 0.7.0 is recorded, but seeds,
full environment pinning and cross-version deterministic reproduction are not
established by that version string alone.

## FEM and exact consumer contract

**Verified source behavior:** P/production/build_section_mesh.py:75-102 assembles
consistent P1 mass and gradient stiffness on every triangle:

```text
C_T = area(T)/12 * (ones(3,3) + I)
G1_T[i,j] = area(T) * gradient(phi_i) dot gradient(phi_j)
```

All vertex degrees of freedom remain. No boundary values or boundary-node
elimination are imposed. **Mathematical inference:** this weak-form Laplacian
corresponds to natural homogeneous-Neumann behavior. The formal higher-order
boundary interpretation remains a design decision, not an explicit historical
boundary-condition specification. It is not a zero-Dirichlet construction.

F/prepare_inputs.py:81-91 solves `G1 U = C U Lambda`, `U.T C U = I`, then exports
`Gp = C U Lambda^p U.T C` for p=2..6. It uses the Python consistent-mass
convention, not an assumed interchangeable fmesher FEM convention.

E/sampler/spectral_live_range_whitening.py:40-163 authenticates the complete
generalized basis and simultaneous diagonalization. With G0=C, nu=5, d=2,
order=6, kappa=sqrt(40)/ell_W, and c=Gamma(5)/(Gamma(6)*4*pi):

```text
Q(ell_W) = c * sum(binomial(6,j) * kappa^(2-2*j) * Gj, j=0..6)
Sigma_full = U diag(1/q_i) U.T
Sigma_A    = U_A diag(1/q_i) U_A.T
B          = U_A diag(1/sqrt(q_i))
L L.T      = B B.T, using positive-diagonal QR(B.T)
```

E/sampler/active_marginal_whitening.py:14-47 constructs that marginal covariance
root. This is not inversion of Q_AA (conditioning), not zero fill and not mode
truncation. All full modes remain; scale-checked roundoff-negative modal entries
can be clipped to zero, which is distinct from dropping modes. Raw-Q amplitude
is preserved; computed reference variances are diagnostic only
(spectral_live_range_whitening.py:209-237).

Active vertices mean nonzero projector columns, not vertices inside a hull.
Geometric support/buffer/interior labels are distinct. Subsetting changed active
counts in S04 159->157, S06 165->164 and S10 168->167.

Historical serialization: mesh_loc.csv; mesh_tv.csv; active_indices.csv;
MatrixMarket A_proj.mtx, fem_C.mtx and fem_g1.mtx..fem_g6.mtx; observation fields
mesh_vertices, active_indices and A_active; preview mesh.rds. The driver reads
MatrixMarket into dense arrays for spectral processing. October 26 tissue
triangles/active indices are zero-based. W's simulation export writes one-based
triangles; build_mesh_only writes R one-based indices and subtracts one on Python
readback. Index bases must be declared, not inferred from extensions. The
scientific arrays were not opened during recovery.

## Direct fields, gallery helpers and flat-model gap

Production direct-W behavior is `W_A = sigma_W L Z`, `W_cells = A_A W_A` for two
coordinate fields. The direct wrapper zeroes the base location offset
(direct_w_dynamic_target.py:16-28). It is distinct from the older displacement
form `s + U(s)`. Paint sine/cosine features use phases `W_cells @ omega.T`
(fixed_splusu_dynamic_target.py:126-144,212-218). No mesh reconstruction occurs
at each update; the reference projector remains fixed.

generate_splusu_phase1.py is a prior-draw gallery. Its ordered_boundary:136-165
rejects multiple boundary components; boundary_path_audit:207-220 checks a finite
path grid. fixed_mesh_interpolator:342-360 rejects plotting queries outside the
fixed mesh. These are not recovered sampler-time nonfolding, containment or
topology guarantees. The direct split-E path requires containment disabled.
This gallery restriction must not be treated as proof that the FEM assembler
cannot represent disconnected domains, or that production enforces one loop.

A separate flat-model implementation with authenticated shared geometry remains
unrecovered. A conceptual identity-coordinate baseline is not an authenticated
artifact or implementation. The design gate must define that comparison.

## Range prior and authenticated numerical measurements

The split-E/direct-W guard and configuration establish:

```text
log(ell_W) ~ Normal(0, .5^2)
log(r_W)   ~ Normal(0, .3^2)
sigma_W   = ell_W * r_W / sqrt(10)
```

The generic parser defaults differ; they are not the enforced split-E prior.
E driver:273-277,389-435 and F driver:276-280,394-440 have identical inspected
blocks. The paint range ell_eta is separate: the base configuration records
fixed .14, not proof of every historical invocation. No new prior is selected.

ell_W has unbounded positive support. Six tested values are .15/.30/.60/1/1.65/2.72.
Approximately 2.2682% of the recorded prior lies above 2.72; .0074048% lies below
.15 (normal-tail calculations, not empirical measurements). A finite test grid
does not certify this prior's domain.

The authenticated READY archive contains all 19 NUMERICAL_VALIDATION.json files.
All report PASS and full-rank/no-truncation. See the
[19-report inventory](ADAPTIVE_MESH_M2_REPORTS.csv),
[exact range aggregates](ADAPTIVE_MESH_M2_RANGES.csv), and
[machine-readable maxima](ADAPTIVE_MESH_M2_NUMERICAL_SUMMARY.json).
These are historical measurements, not rerun matrix validation. Each report's
covariance comparisons use at most 256 selected observation rows.

| Check | Maximum across reports |
| --- | ---: |
| Active versus full projected covariance | 1.2696980907159972e-15 |
| QR covariance-root reconstruction | 1.4033777182161902e-15 |
| Root derivative identity | 2.2588960222802387e-15 |
| Independent covariance finite difference | 6.895432725771302e-09 |
| Mass orthogonality | 2.4670009038999306e-15 |
| Generalized eigenpair residual | 2.7071028552458233e-15 |
| Simultaneous diagonalization | 4.665209496402143e-15 |

| ell_W | Continuum relative covariance discrepancy across sections | Projected variance extrema |
| ---: | ---: | ---: |
| .15 | .127887-.175438 | .611449-1.126190 |
| .30 | .043392-.059771 | .836982-1.024079 |
| .60 | .015840-.020557 | .936459-1.004387 |
| 1.00 | .007622-.009573 | .971981-1.014042 |
| 1.65 | .124054-.176062 | 1.070512-1.347583 |
| 2.72 | .588065-1.356456 | 1.519212-2.550450 |

**Excellent discrete full-to-active agreement does not establish continuum
fidelity.** Fidelity is inadequate for a blanket short/long-range continuum
accuracy claim: discrepancies are substantial at .15 and especially 2.72.
No canonical scientific error threshold has yet been chosen. The historical
validator treats continuum comparison as diagnostic, not a PASS gate. No report
failed its discrete criteria. The reports do not isolate boundary error from
resolution error and do not vary buffer extent or resolution. They are not a
buffer-sensitivity or convergence study. A finite-domain prior might itself be
the intended model; that requires an explicit scientific decision.

M1 also recovered geometry metrics for all 19 sections: full-glial active counts
152-181, total vertices 334-372, recorded minimum angle approximately >=25 degrees;
maximum row-sum and coordinate errors 2.220446049250313e-16, area difference
8.881784197001252e-16, boundary-distance difference 4.440892098500626e-16.
These records are preserved in geometry_preview_summary.json. All 19 input
certificate hashes match C's bundle manifest and equal committed B3 records;
all 19 GPINIT source hashes/counts match their observation certificates. This
is recorded downstream consumption, not certification of actual sampler launch.

## Scientific design gate

The [decision ledger](ADAPTIVE_MESH_DECISIONS.csv) keeps each choice unresolved:

1. Choose finite-domain prior versus continuum approximation and error criteria.
2. Authenticate units or retain source_native; explicitly choose any separate
   numerical transform and its population.
3. Choose tissue-support cells independently of modeled observations.
4. Specify anatomical holes, disconnected pieces and separate brains; distinguish
   anatomical holes from withheld observations.
5. Specify boundary behavior and buffer extent against the intended range prior.
6. Design a bounded resolution/buffer accuracy and resource study; vertex count
   alone must not define scientific acceptance.
7. Freeze consistent mass, full spectrum, marginalization, indexing, serialization
   and independent projector identity checks.
8. Define an authenticated flat/warped comparison and any topology constraints.
9. Pin geometry environment/ordering and preserve plot-generation commands and
   explicit review records.

No original September source, original sensitivity study, cells.csv generation
record or exact October 30 contact-sheet generation attestation was recovered.
Their absence does not prove historical procedures wrong or permanently lost.
