# Canonical BSFM sampler architecture

Status: **selected by explicit user decision; first Gaussian/shrinkage/PX layer
implemented and validated; full sampler not yet ported**. See the bounded
[layer-1 report](../sampler/LAYER1.md) and [source map](../sampler/LAYER1_SOURCE_MAP.csv).
The deterministic full-spectrum warp/active-marginalization Layer 2 is implemented
and validated; see the [layer-2 report](../sampler/LAYER2.md). Its CPU validation does
not select a GPU production environment or implement the remaining sampler.
The frozen L16/direct-W factor target Layer 3 is implemented and validated; see its
[implementation and validation report](../sampler/LAYER3.md). It reuses the
accepted CPU environment and does not implement NUTS, factor chronology or a
complete sampler. No scientific choice in this architecture is changed.
Decision date: 2026-11-02. Recovery baseline:
`10cb6e27168aae7581831a6591089b4d88629c49`.

The user accepted the [bounded nomination](../recovery/BSFM_SAMPLER.md) and
selected the F/C production-overlay architecture for conservative consolidation.
This is architectural authority, not a claim of a completed/converged historical
F campaign or a newly validated canonical sampler. Source paths, byte identities
and evidence classes are in the [source table](../recovery/BSFM_SAMPLER_SOURCES.csv).

Selected driver: `sampler/run_c3full_fixed_profile_nuts.py`, 94890 bytes,
SHA-256 `eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`.
F and C/code copies are byte-identical. Selection follows source/manifest evidence
and explicit user approval, not folder labels or recency.

## Frozen scientific and computational invariants

- Use the recovered Gaussian factor model and priors, type-specific loadings,
  gene-specific noise shared across types, fixed sharing s=0.20 and MGP shrinkage
  on B=alpha*Lambda. Preserve driver-level prior constants, including later-delta
  shape 1.5 and log-alpha variance 0.7.
- Consume the immutable final centered modeling Y separately from GPINIT.
  No second logarithm, variance scaling, replacement by a smoothed surface or new
  response centering is authorized. Preserve explicit cell/gene/type identities.
- Use direct-W coordinates, with factor-specific live warp range/amplitude and
  sigma_W=ell_W*r_W/sqrt(10). Preserve independent log-ell N(0,.5^2) and log-r
  N(0,.3^2) priors, shared by the two coordinate dimensions within each factor.
- Preserve the full-spectrum raw-Q FEM law and exact active marginalization.
  Outward-buffer vertices are integrated out; do not condition them to zero,
  truncate modes or normalize away the range-dependent raw-Q variance.
- Preserve the recorded L16 finite-feature factor target with fixed ell_eta=.14.
  Exact-SE continuum/kernel diagnostics do not replace that likelihood.
- Preserve three conjugate Lambda/joint-eta/sigma2 subcycles, then phi/delta/tau,
  then invariant PX-alpha refresh, then random factor visitation.
- Preserve split-E: field NUTS on log-alpha/logit-zeta/zW; fixed-physical-W
  NUTS on log-ell/log-r; rewhiten the same W; draw eta once; refresh fitted Y.
  No eta redraw between the two NUTS blocks. Rebuild current conditional context
  rather than reusing a cached density/gradient from an earlier Gibbs state.
- Preserve Gaussian perturb-and-solve joint eta and its checked numerical error
  bound, the independent target/gradient checks, and physical-W/PX invariants.
  No silent jitter, clipping or tolerance changes are authorized.
- Preserve sequential retained warmup endpoints and frozen post-warmup tuning.
  Support complete checkpoint restart and explicit readaptation-on-resume.
- Save complete coherent state atomically at sweep boundaries, including RNG,
  spectral chart and tuning; retain sufficient posterior state for reconstruction.
  Diagnostics and completion status must expose divergence/fidelity warnings.
- Keep native real-data factor coordinates. Sign/label alignment used by
  simulation diagnostics must not become an unapproved sampler transition.

The exact equations, source lines, historical numerical settings and restart
semantics are recorded in the recovery document. These invariants must be ported
conservatively, not replaced by an open-ended statistical redesign.

## Noncanonical branches

LI-ESS, Fisher ESS, conditional Fisher ESS and LI-NUTS are experimental and
**not selected**. They are absent from F/C; no promotion evidence was recovered.
No claim is made that they improved or worsened ESS/second or R-hat. No search
for their missing result files is required.

Joint unsplit NUTS, identity-plus-displacement variants, live outer-range/floor
experiments, containment, fixed loading precision, simulation generators and
legacy incomplete-checkpoint conversion are not selected paths. The historical
run wrappers remain provenance only. No flat fitting implementation is selected.

## Bounded port organization and extraction rule

**Do not copy the entire 340313-byte c3_established_functions.py.** Extract only
the following six functions used by the nominated path, preserving formulas,
driver overrides, source hash and original source-line provenance:

| Function | Original F source lines | Intended module responsibility |
| --- | --- | --- |
| compute_Yhat | 2849-2869 | model/state contracts or signal evaluation |
| compute_qgk | 2817-2846 | shrinkage and PX |
| sample_Lambda_twostage | 6936-7026 | conjugate updates |
| sample_sigma2_twostage | 7193-7216 | conjugate updates |
| sample_phi | 3886-3913 | shrinkage and PX |
| sample_delta_tau | 3859-3879 | shrinkage and PX |

Apply the same rule to other broad helpers: from generate_splusu_phase1.py take
only required FEM constants (28-35) and dense_mm (55-59); from
splusu_active_tqff_target.py take only barycentric_triplets (13-38). Do not carry
their generators or alternative targets into the canonical dependency surface.
Extract the used diagnostic functions from broader helpers where appropriate.
Keep a source-to-port provenance map; removing unrelated code must not alter
formulas, array order, RNG consumption or partial-collapse chronology unnoticed.

The future implementation must use small modules with these responsibilities:

| Responsibility | Required boundary |
| --- | --- |
| Model/state contracts | Explicit Y, mesh, rule, GPINIT, axes, parameter shapes and immutable identities |
| Conjugate updates | Gaussian loadings, joint eta perturb-and-solve, gene noise |
| Shrinkage and PX | qgk, phi/delta/tau, amplitude refresh and invariant checks |
| Spectral active marginalization | Full FEM basis, raw modal law, QR root/derivatives; reuse validated canonical machinery only after equivalence checks |
| Direct-W feature target | Physical coordinate map, deterministic features, collapsed sufficient statistics/value/gradient |
| Split-E targets/transitions | Field block, fixed-W hyper block, rewhitening and adaptation |
| Factor chronology | Three subcycles, shrinkage/PX, random visitation, one post-transition eta draw |
| Checkpoint/restart | Complete atomic state, RNG/chart/tuning restoration, explicit readaptation |
| Diagnostics and retained draws | Trace/certificate semantics, warning visibility, reconstructable retained state |

This is an implementation plan, not authorization to import or implement code in
this documentation step. A later conservative port requires bounded mechanical
regression and review; it must not start an alternative-method comparison.

## Configurable and unresolved choices

This decision does **not** choose K, chain count, warmup length, settling length,
production length, save cadence, run destination or execution platform. Historical
K5/K20/K25 schedules are evidence, not universal scientific choices. Readaptation
is supported explicitly; enabling it for a particular run remains a run-spec choice.

Environment materialization, complete dependency/source locks, canonical
completion-status handling, and software/environment authentication in checkpoints
remain implementation work. Historical command defaults must not silently
override the selected model. Physical coordinates remain source_native until
separately authenticated; the canonical mesh's explicit normalization remains
the sampler-coordinate handoff.

The [full-data response contract](MODELING_RESPONSE_HANDOFF.md) and
[GPINIT contract](../initialization/C3_GP_SVD.md) remain in force. Full-data
preprocessing is ineligible for primary holdout scoring. Training-only holdout
preprocessing, matched flat fitting, prediction and sampler studies are outside
this decision. No HPC work is authorized.
