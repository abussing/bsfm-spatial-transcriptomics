# October 26 warp-basis recovery and conservative port

Status: **accepted canonical practical mesh implementation**, following explicit
user approval of the corrected port and byte-identical S10 reproduction.
No all-section execution or production promotion is implied. The
[user decision](../decisions/ADAPTIVE_MESH_WARP_BASIS.md) replaces continuum-based
production selection with a parsimonious latent-warp basis objective.

## Bounded source identities

A = `D:\johnston_brain\artifacts\MESH_LINEAGE_AUDIT_20261026`.
F = `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1`.
P = `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_19_SECTION_PRODUCTION_20261024`.
E = `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CURRENT_20261014\bayesian_spatial_factor_model`.

A and F `build_preview.R` are byte-identical, 8,346 bytes, SHA-256
`a343fcb0e819976b3982f6d1d77e89faa021c5ccd13dc508f8170f428832a66f`.
The [new source identity record](audits/october26_S10_20261102/source-identities.json)
contains exact paths, sizes, hashes and inspected lines. The existing
[source ledger](../recovery/ADAPTIVE_MESH_SOURCES.csv) also identifies P's
preparation/FEM sources. The four small E sampler modules read here match their
F counterparts byte-for-byte; the F production driver has its separately recorded
hash. These files were read as evidence, never imported or executed.

Only the named roots and directly referenced S10 inputs/outputs were inspected.
The A source directory contains three preview sections, not S10; F contains the
complete S10 source geometry, inherited old mesh, preview and prepared mesh.
No HPC connection, new drive-wide search or environment archaeology occurred.

## Verified mesh-to-warp flow

| Transition | Implemented behavior | Exact historical source |
| --- | --- | --- |
| Glia → reference locations | Stable MIC/AST/OGC blocks; componentwise minimum subtraction, common maximum-span divisor per section. No rotation/reflection. | P `production/prepare_sections.py:58–76,94–99` |
| Reference locations → mesh | Full glial geometry, nonconvex hulls, four stages, inherited old outer edges, bounded h adaptation. | A/F `build_preview.R:42–86` |
| Mesh → cell projector | P1 barycentric basis at unchanged reference locations; drop entries with abs value below 1e-14; active = nonzero columns. | A/F `build_preview.R:68–84` |
| Full geometry → thinned observations | Within-type Morton ordering, retain every other cell, subset projector rows and recompute active columns. No rebuild of vertices, triangles or FEM. | F `prepare_inputs.py:19–25,35–58,77–91` |
| Mesh → FEM | Consistent triangle mass `area/12*(ones+I)` and gradient stiffness; no boundary elimination. Full generalized eigensystem generates G2…G6. | P `production/build_section_mesh.py:75–102`; F `prepare_inputs.py:81–91` |
| FEM → full prior | Simultaneous modal diagonalization of C and G1…G6, authenticated without truncation. Evaluate historical raw Q, not a variance-normalized replacement. | F `code/sampler/spectral_live_range_whitening.py:40–158,163–237` |
| Full prior → active vertex values | Positive-diagonal QR of the weighted full-spectrum active rows gives L; inactive vertices integrated out exactly. | F `code/sampler/active_marginal_whitening.py:14–47` |
| Active values → cell warp | Per factor, `W_A = sigma_W * L * Z`, where Z has shape n_active × 2; `W_cells = A_active * W_A`. Same geometry, L, range and amplitude for both coordinate columns. | F `code/sampler/active_marginal_whitening.py:50–59`; `fixed_splusu_dynamic_target.py:106–123,210–218` |
| Direct W chart | Wrapper sets the base reference-coordinate offset to zero. Thus production uses direct warped coordinates, not `s + W`. | F `code/sampler/direct_w_dynamic_target.py:16–28` |
| Warped cells → factor dependence | Deterministic frequency rule: phase = W_cells × omega.T; paired weighted cosine/sine features. Warp changes phase distances, inducing nonstationary dependence in original coordinates. | F `code/sampler/fixed_splusu_dynamic_target.py:131–149,479–501` |
| Sampler consumption | Loads C, G1…G6, full projector, active indices and A_active; builds full spectral artifact and passes U[active] plus projector triplets to each factor target. | F `code/sampler/run_c3full_fixed_profile_nuts.py:335–345,398–440` |

The sampler uses a separate whitened Z and hyperparameters for each factor, with
two coordinate columns sharing that factor's geometry and covariance parameters.
The inspected prior is isotropic across those two columns. This does not assert
posterior independence of the two dimensions after conditioning on expression.

For each factor the implemented feature covariance is
`alpha^2 * [zeta * Phi(W) Phi(W).T + (1-zeta) I]` (mathematical reading of the
feature/nugget construction). Gene/type loadings Lambda remain separate:
F driver's lines 1482–1488 explicitly record this and distinguish temporary
`alpha*Lambda` algebra from the statistical parameterization. The sufficient
statistics at `fixed_splusu_dynamic_target.py:412–430` use type-specific loadings.
Warp amplitude sigma_W controls spatial coordinates, not response amplitude.
The direct-W wrapper maps `log_sigma_W = log_ell_W + log_r_W - log(sqrt(10))`;
this is recovered sampler behavior, not a newly implemented sampler prior.
There is no empirical claim here that these scales are identifiable in real data.

## Exact marginalization and boundaries

The full generalized eigenvectors satisfy `U.T C U = I`. Modal precision uses
`q_i = (1/(20*pi)) * sum_j binom(6,j) * kappa^(2-2j) * d_ji`,
`kappa = sqrt(40)/ell_W`, with d_ji the authenticated diagonal of `U.T G_j U`
and G0=C. All modes remain; recorded roundoff-negative entries are checked and
clipped as in the source. There is no diagonal renormalization.

Set `B = U[active,:] diag(q^-1/2)`. Positive-diagonal QR of B.T gives L with
`L L.T = B B.T = Sigma_full[active,active]`. Because inactive projector columns
are zero, full-to-cell and active-to-cell representations agree. This is
marginalization, not `inverse(Q[active,active])`, zero conditioning, removal of
outer FEM vertices, or spectral truncation. Natural-Neumann behavior is a
mathematical inference from the weak FEM assembly without Dirichlet elimination.

Prior contours retained as internal constraints are not declared hole boundaries.
No new topology policy for disconnected tissue pieces is introduced. The inherited
far polygon remains an explicit dependency. Physical coordinate units, historical
flat-model coupling on authenticated shared geometry, and an observed true warp
remain **not found/not established** as applicable; none is invented here.

## Canonical builder and explicit interface

- [october26_builder.R](../../src/bsfm/mesh/october26_builder.R) conservatively
  ports the selected builder's geometry/adaptation operations. It removes the
  19-section loop and plotting, requires explicit input files, isolates the R
  library, and emits metadata. It preserves original vertex/triangle order.
- [october26.py](../../src/bsfm/mesh/october26.py) ports the normalization,
  Morton regression subset, consistent FEM assembly and polynomial export;
  evaluates the full modal law and QR marginal for a bounded mechanical check.
  It never imports historical modules and does not implement Gibbs/NUTS.
- [october26-warp-basis.json](../../config/mesh/october26-warp-basis.json)
  records all preserved settings and mechanical comparison tolerances.
- [test_mesh_october26.py](../../tests/test_mesh_october26.py) covers transform,
  projector support/affine identities, zero/known displacement, thinning reuse,
  consistent FEM, dense Schur-complement marginalization and corrupted inputs.

Array contracts are explicit: vertices `(V,2)`, zero-based triangles `(T,3)`,
full projector `(N,V)`, sorted active global indices `(A,)`, active projector
`(N,A)`, full C/G1…G6 `(V,V)`, full U `(V,V)`, modal diagonals `(7,V)`,
source rows/types `(N,)`, two warp columns `(A,2)`. Local active-projector columns
map through the global active-index vector. Source coordinate order stays
`[center_y,center_x]`; CSV x/y names are historical aliases, not verified physical
axis labels. No coordinate swap or unit conversion is applied.

The regression export has little-endian logical SHA-256 values using
the existing mesh identity encoding (sorted JSON dtype/shape, LF, C-order bytes),
plus whole-file hash and closed-file readback. The first attempt did not reach this export. The single corrected S10 rerun
reached it and passed the bounded closed-file handoff checks. The full production bundle
and sampler port are outside this step.

## S10 result and stopping point

The [first audit](audits/october26_S10_20261102/README.md) preserves the failed
330-vertex attempt. The [bounded localization](audits/october26_S10_localization_20261102/README.md)
identified the precise defect: JSON integer 25 was not accepted by the native
fmesher NumericVector angle reader, leaving its 21-degree default active.
Converting only that setting to double 25 restored the requested mechanics.

The one authorized rerun produced byte-identical historical vertices, triangles,
projector and mesh RDS: 371 vertices, 708 triangles, 168 full-cell active vertices,
167 historical-half active vertices. FEM relative disagreement is at most
6.23e-15; exact-marginalization errors are below 8.32e-16. Coordinates, boundary,
settings and environment were otherwise unchanged. No parameter study occurred.

The user's clarification controls interpretation: no count is scientifically
sacred. The geometry covers the modeled cells, coarsens outward, and has a
practical low-dimensional warp basis. Exact equality here diagnoses a porting
error; it is not a universal production acceptance criterion or proof of the
true or optimal warp. Missing historical intermediate stage arrays remain
explicitly unrecovered rather than inferred from matching final outputs.

All 126 Python tests passed before localization, including seven new tests and
the existing synthetic R-bridge integration tests. After the narrow correction,
all eight bounded tests passed, including the actual JSON/R/native-option
boundary regression. Historical inputs remain unchanged. Phase-0 v1/v2 remain
failed external evidence. No commits, production promotion, fixed-artifact
fallback, GP initialization, MCMC or HPC work. The corrected port is now accepted for canonicalization.

## Canonicalization acceptance

Outward grading and exact inactive-vertex marginalization are load-bearing.
The canonical implementation is `bsfm.mesh.october26.build`, with the frozen
`config/mesh/october26-warp-basis.json` configuration and its R bridge. The module
CLI is a bounded S10 historical regression, not an all-section launcher.
M3/Phase-0 range-derived geometry is rejected for production and retained only
in the [historical receipt](REJECTED_PHASE0.md) and Git history. The subsequent
[active-code cleanup](audits/active_cleanup_20261102/README.md) removes its launcher,
configurations, schemas and study-specific tests. The canonical builder,
configuration, numerical dependencies and S10 reproduction records are unchanged.
The accepted isolated environment retains its original machine-local path (whose
name includes `phase0`); that path is an environment identity, not another mesh
entry point. Reusable numerical helpers do not define a geometry selection policy.

The permanent angle test now invokes the actual Python `build()` command path,
passes the real JSON configuration to the actual R builder prefix, verifies
double 25 in fmesher options, and rejects a test-only mutant with the conversion
removed. It stops before mesh construction. See the [acceptance test record](audits/october26_acceptance_20261102/README.md).
