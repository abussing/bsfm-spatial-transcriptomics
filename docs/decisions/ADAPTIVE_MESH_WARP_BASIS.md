# Adaptive mesh as a latent warp basis

Authority: explicit user scientific correction and scope reset following
`4e362b6b3988e1b899d4250812ddfc4040beb819`. This supersedes the
[rejected M3/Phase-0 design](../mesh/REJECTED_PHASE0.md), not the preserved
[M1/M2 historical evidence](../recovery/ADAPTIVE_MESH.md).

The mesh is primarily a low-dimensional basis for the unknown latent spatial
warp. Smooth movements of modeled cells allow a GP stationary in warped space
to induce nonstationary dependence in tissue coordinates. Real data have no
observed true warp or gold-standard cell movement.

The production objective is a parsimonious mesh permitting scientifically useful,
smooth, learnable deformation, regularizing the latent warp while keeping repeated
Gibbs/NUTS updates practical. Infinite-domain Matérn agreement over extreme prior
ranges is not a production selection criterion. It may remain a labeled diagnostic.
Neither mechanical reproduction nor a small vertex count proves scientific optimality.

The user selected the October 26 four-stage fmesher construction for conservative
canonicalization. The corrected builder is **accepted as the canonical practical
mesh implementation** by explicit user approval. The first S10 reproduction failed;
a bounded localization identified an R integer/double angle-argument defect.
The one corrected rerun passed. See the [report](../mesh/OCTOBER26_CANONICALIZATION.md).
The user clarified that exact counts are not sacred: reproduction is a mechanical
regression check, not a scientific selection criterion or requirement for other
sections. Adaptive coverage, smooth outward coarsening and practical active
dimension are the objective. No fixed-artifact fallback was needed.

Preserve these historical mechanics:

- Geometry uses every modeled MIC/AST/OGC cell, before observation thinning.
- Subtract the glial componentwise minimum; divide both axes by the maximum
  glial axis span, separately by section. Preserve `[center_y, center_x]`.
  Physical units remain unauthenticated, `source_native`.
- Use the nonconvex hull, padding `.02/.18/.45`, four explicit stages, and the
  inherited far outer boundary as an explicit required input. No replacement
  boundary is authorized.
- Preserve h adaptation toward 175 active vertices (acceptable 150–200), cutoff,
  and the 25-degree requested minimum angle. These are historical mechanics,
  not claims of an optimal warp basis.
- Preserve consistent P1 FEM, the full spectrum and exact inactive-vertex
  marginalization; no conditioning away outer vertices or amplitude rescaling.
- Preserve the distinction between direct-coordinate production warp values and
  identity-plus-displacement helpers. Zero-displacement tests establish projector
  mechanics; they do not change the production chart to identity-plus-displacement.

The [configuration](../../config/mesh/october26-warp-basis.json) is the canonical
builder's explicit parameter record. S10's historical 371 vertices / 708 triangles
serve 9,422 geometry cells. There were **168 active vertices for all those cells**
and **167 for the 4,712 retained historical observations**. Reproducing the latter
does not authorize thinning the canonical full-data responses.

M3 and Phase-0 v1/v2 are preserved as a rejected experimental redesign. No Phase-0
v3, new sweep, sensitivity study, fit, holdout experiment, GP initialization or
MCMC is authorized here. Capability work is consolidation: conservative port,
bounded reproduction, review. Further scientific redesign needs explicit approval.

Acceptance is limited to the corrected conservative port and bounded S10
mechanical reproduction. Outward grading and exact inactive-vertex
marginalization are load-bearing. No all-section run, GP initialization, Gibbs
sampler or HPC execution is authorized in this checkpoint. The subsequent
[bounded cleanup](../mesh/audits/active_cleanup_20261102/README.md) removes the
rejected study surface without changing this builder or its numerical dependencies.
