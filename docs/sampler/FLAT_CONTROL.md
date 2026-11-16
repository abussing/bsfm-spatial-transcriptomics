# Stationary factor control

For a comparison with a stationary model that can learn its spatial scales,
use `model: flat` and an explicit `flat_range_prior` in the external run recipe:

```json
"flat_range_prior": {"median": 0.18, "log_sd": 0.25, "initial": 0.14}
```

These numbers illustrate the recovered historical log-range prior family; they
are not universal defaults. The median and initial range use the prepared
coordinate units. Declare them before fitting and do not select them using
held-out outcomes. Each factor has an independent range with
`log(ell_eta[k]) ~ Normal(log(median), log_sd**2)`. There is no hard range floor,
soft short-range penalty or shared-range constraint. The normal prior is evaluated
in the sampled log coordinate; adding another log-Jacobian would be incorrect.

Omitting `flat_range_prior` preserves the historical fixed-range control:
every factor uses `ell_eta=0.14`, and only log-alpha/logit-zeta are sampled.
Label results from that mode **fixed-range flat**. They do not establish an
advantage over a stationary model with learned ranges. Deep's fixed outer range
does not impose the same restriction: its inferred warp can expand and contract
physical distances. This extension leaves the accepted deep target unchanged.

## Likelihood and transitions

The learned-range position has exactly three coordinates:
`[log_alpha, logit_zeta, log_ell_eta]`. Physical coordinates remain the centered
original tissue locations. For the authenticated reference rule at 0.14, scale
each frequency by `0.14/ell_eta[k]`, retain the weights and cosine-then-sine order,
and use the resulting finite features in

`alpha[k]^2 * (zeta[k] * Phi[k] @ Phi[k].T + (1-zeta[k]) * I)`.

This finite-feature covariance is the implemented likelihood. The continuous SE
kernel is not substituted for it. Range changes enter both its determinant and
quadratic term. `finite_features.likelihood_parts` supplies the analytic
log-range derivative; the loading/amplitude and zeta priors are unchanged.
All three coordinates receive joint NUTS transitions and window adaptation at
target acceptance 0.9. There is no warp transition or warp prior in this model.
Both single-factor and joint eta updates use the current factor ranges.

## Saving, resuming and predicting

The prior, mode and three-coordinate order are part of target/checkpoint
identity. Genesis, tuning, retained records and checkpoints use the target's
declared dimension. `ell_eta` contains the actual per-factor posterior ranges.
`W_cell` and `W_active` remain identity-coordinate fields; the common record's
`ell_U` and `sigma_U` arrays are ones in this mode, explicitly neutral transport
values with no inferred warp interpretation. Existing fixed-range records retain
their original meaning and must be read using their pinned source commit.

At every saved draw, prediction uses that draw's range for **both** training and
query features. Eta and observation noise are integrated conditionally as before;
posterior summaries average over the saved ranges rather than substituting their
posterior mean. A range/position mismatch is rejected. Do not restore a learned
range run as a fixed-range target, or change priors on resume.

## Provenance and validation

The range-dependent feature algebra and derivative already occur in the accepted
[Layer-3 source map](LAYER3_SOURCE_MAP.csv). The historical
`fixed_splusu_dynamic_target.py` source with SHA-256
`b172a3732b30c2e15387ad898565a1c9971d902352d9bfd54485a7937295748e`
contains the optional normal-in-log-range prior and gradient at lines 239â€“245.
The historical driver with SHA-256
`eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`
declares median 0.18 and log SD 0.25 at lines 1734 and 1738. This recovers the
prior form and defaults; it does not establish equivalence to every historical
flat run. This stationary three-coordinate integration is a new implementation.

`tests/test_flat_range.py` checks values and all three derivatives against an
independent dense Gaussian calculation at several ranges, per-factor prediction
against dense conditioning, and periodic interruption/restart, retained ranges,
RNG preservation, non-replay and retuning. Existing deep and fixed-flat tests
guard their behavior. CPU checks alone do not certify a GPU deployment or
scientific convergence. Keep deployment receipts and analysis recipes external.
## Conditional geometry audit (experimental)

`python -m bsfm.sampler.flat_geometry_audit --plan EXTERNAL_JSON --commit SHA`
compares inherited tuning, ordinary diagonal retuning, and diagonal retuning in
log spatial/nonspatial variance coordinates on authenticated saved flat
conditionals. This is a diagnostic only: it does not alter the production runner,
resume a scientific fit, or establish full-Gibbs mixing. The external plan pins
each recipe, genesis, conditional NPZ and source report, plus seeds, warmup length,
draw count, output and source commit. HPC authorization requirements still apply.

The alternate coordinates are `s=log(alpha^2*zeta)` and
`n=log(alpha^2*(1-zeta))`. The inverse is
`log(alpha)=logaddexp(s,n)/2`, `logit(zeta)=s-n`, with constant absolute
Jacobian determinant `1/2`. The complete existing density and priors are pulled
back, including this constant; no independent variance priors are substituted.
The coordinate identity, covariance, density measure and full flat-target
gradients are tested in `tests/test_variance_coordinates.py`. This algebraic
validation alone is not evidence of a faster or production-ready sampler.

For deep or flat failures, `sampler.transition_replay_audit` reconstructs one
published factor transition from an authenticated earlier checkpoint and checks
its acceptance, divergence and integration-step diagnostics against the original.
It then records scalar curvature and fixed-duration energy-error refinement at
that exact incoming conditional. Its external plan pins recipe, source checkpoint,
expected diagnostics, factor and sweep. Outputs are diagnostics only. A replay
mismatch fails before causal interpretation; local curvature and energy checks
do not certify mixing or change production stop rules.

`sampler.conditional_curvature_audit` can follow a replay with finite-difference
Lanczos estimates of field curvature and directional gradient checks. An explicit
counterfactual changes whitening hyperparameters while preserving physical W and
likelihood statistics. This changes both the physical prior and the coordinate
map; it does not isolate a coordinate-only cause. The external plan authenticates early/late captured conditionals, recipe
and genesis. Ritz estimates and counterfactuals are local diagnostics, not samples
or a justification for altering priors, meshes or convergence criteria.
Its optional `mode: metric` compares inherited tuning, a halved step, and a
transported constant field metric at the same captured conditional. For
`W=B z`, transport uses `D_new=T D_old T^T`, `T=B_new^-1 B_old`, with two warp
columns and unchanged scalar coordinates. Hyperparameters are held fixed during
each field trajectory, so this diagnostic uses ordinary Euclidean NUTS. It is
not production integration, RMHMC, or evidence of full-Gibbs convergence. Seeds
and diagnostic draw count must be frozen in the external plan.

For causal diagnosis, the replay plan can opt into `capture_boundaries: true`.
`GibbsSweep.sweep(observer=...)` supplies detached snapshots after each loading,
joint-factor, noise, shrinkage and PX update, and around each factor update.
Observers must not consume global random numbers. The default path performs no
snapshot work. The recorder saves only the selected factor's sufficient
statistics, position, tuning and state hashes. The selected deep transition
also exposes its field endpoint and fixed-physical-warp hyperparameter endpoint
through the same kernel used in production. Capture remains provisional unless
the published transition's diagnostics reproduce. No retuning or continuation
is performed by this audit.

`boundary_diagnostics.fixed_chart_field` permits separate prior and coordinate
counterfactuals: hold the physical warp, likelihood statistics and physical
prior fixed when changing the coordinate root; hold the coordinate root fixed
when changing the physical prior. It includes the two-column log Jacobian.
Transport inverse mass and momentum together for an equivalent physical kinetic
law; an inherited diagonal metric is a separate experimental arm. Compare
physical warp and finite-feature covariance changes, not raw whitened-coordinate
differences across different roots. Fixed-duration energy probes are diagnostic
paths, not the actual adaptive NUTS tree. Local improvements do not establish
sustained Gibbs efficiency. Interactions between conditional changes remain
possible and must not be forced into a single-update explanation.

For bounded original-flat diagnostics, `sampler.flat_replay_profile` replays a
Gibbs prefix twice with identical saved state and RNG, times synchronized calls,
and captures selected-factor conditional changes. It rejects alternate transition
policies and uses only log amplitude, logit spatial fraction and log range.
The external plan pins source commit, recipe, checkpoint prefix and expected
transition diagnostics, with an internal limit of at most 40 minutes. Cross-runtime
imports retain the migration checks; differing transitions remain explicitly
unverified rather than being claimed as exact reproductions. Timing separates
first compilation from warmed operations; neither pass adapts or continues a fit.
