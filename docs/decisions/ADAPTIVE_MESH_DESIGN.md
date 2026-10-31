# Canonical adaptive-mesh scientific design

Status: **broad scientific design and staged study protocol approved; no mesh
implementation, numerical resolution, grading or buffer selected for production**.
Decision baseline: `35a22212528d24daba218e48da54a9f8ee8f0c76`.
Authority: the user's explicit approval of the amended M3 design and staged
protocol. This checkpoint authorizes documentation, not Phase 0 execution.

Evidence: [M1/M2 recovery](../recovery/ADAPTIVE_MESH.md),
[M3 preservation receipt](../mesh/audits/M3/README.md), and the
[canonical response handoff](MODELING_RESPONSE_HANDOFF.md).
The original M3 proposal is preserved unchanged as evidence; this decision takes
precedence over its amplitude coupling, two-grading workload and tail-policy
proposals. No historical implementation is promoted.

## Frozen scientific choices

### Target covariance

The numerical target is a unit-amplitude stationary continuum Matern reference
field with smoothness nu=5, practical range ell, and kappa=sqrt(40)/ell.
At separation d, write t=kappa*d:

```text
rho(d) = 2^(1-nu) / Gamma(nu) * t^nu * K_nu(t)
rho(0) = 1
```

The finite FEM boundary is approximation machinery, not an intended arbitrary
scientific boundary effect. Compare the numerical covariance against this
independent analytic target; do not rescale its diagonal to conceal errors.
The recovered direct-coordinate warp construction is compatible with this
reference-field target. A composed deep/warped response is not thereby asserted
stationary, and an identity-plus-displacement model is not introduced.

The historical `sigma_W = ell*r/sqrt(10)` relationship is **recovered sampler
behavior, not a frozen mesh requirement**. Its final authority and coupled
derivatives belong to later sampler recovery. This study evaluates unit amplitude.
The SPDE/FEM interpretation and boundary motivation were considered in M3 using
[Lindgren et al.](https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2011.00777.x)
and [boundary-truncation analysis](https://arxiv.org/abs/1809.07570); neither is a
certificate for the as-yet-unbuilt canonical adaptive meshes.

### Support, observations and coordinates

All eligible cells in each canonical registered section define empirical tissue
support. Every canonical MIC/AST/OGC modeling cell defines an observation-projector
row, preserving its canonical identity and order. Projector activity is algebraic
(nonzero projector columns), separate from tissue/support/collar/buffer labels.

Known cell locations may remain in fixed geometry during expression holdout.
Held-out expression values must not enter training-only response preprocessing
or fitting. Cross-validation holdout holes never alter canonical geometry.

Preserve raw coordinates unchanged in `[center_y, center_x]` order with
`source_native` units and physical unit declaration `not_found`. Derived mesh
coordinates and the algebraically exact inverse are:

```text
o_s = componentwise minimum over all eligible section cells
S   = 6532.1214803230505 source_native
z_s = (x - o_s) / S
x   = S*z_s + o_s
```

Record origin, scale, both coordinate axes and source identities. Preserve raw
float64 values; the inverse formula does not promise bitwise floating-point
roundtripping. No rotation, reflection or axis swap is introduced.

This common scale replaces historical section-specific glial max-span scaling.
Retaining the historical numerical range prior under this common scale is an
explicit scientific prior-coordinate decision, not a formatting detail: native
range medians become common instead of section dependent. No physical-unit or
cross-section calibration claim follows from this choice.

### Sections and topology

Treat all 19 registered sections independently, including both metadata-separated
S12 sections. Never infer animal identity from a section suffix.
The initial model uses a connected ambient computational domain enclosing each
section's all-cell support. Do not automatically turn apparent holes or cell-free
gaps into internal Neumann boundaries. Computational bridging does not establish
anatomical continuity. Preserve measured component, gap and hole diagnostics as
metadata for review and possible future barrier models.

For the bounded experiment, use an all-cell convex-hull enclosure with the
specified fine collar and buffer. This is an experimental enclosure rule, not
an anatomical support classifier or a selected production boundary algorithm.
M3's disk/radius thresholds remain diagnostic scales, not approved anatomical
thresholds. Near-coincident observations are not removed or jittered.

## Frozen FEM and consumer requirements

- Consistent P1 mass matrix and ordinary gradient stiffness matrix.
- Natural outer-boundary weak form; no imposed zero boundary values.
- Full retained domain and full spectrum; no silent spectral truncation.
- Exact active marginal covariance; never condition inactive vertices to zero.
- Separate geometric-region labels and algebraic active-vertex identities.
- Zero-based canonical vertex and triangle indexing.
- Authenticated sparse serialization with declared shapes, dtypes, byte order,
  index convention, duplicate handling, logical hashes and file hashes.
- Explicit coordinate axes, cell IDs/source rows, vertex IDs and region labels.
- Independently validated observation projectors: all-row coverage, membership,
  row sums, barycentric weights and affine coordinate reconstruction.
- The same authenticated reference geometry for flat and deep/warped comparisons.

Sparse mass/stiffness/projector artifacts and dense derived covariance/root
artifacts must be distinguished. Exact file layout and environment are still
implementation decisions. Natural behavior is defined by the weak-form operator
and its full spectral construction; no separate high-order physical boundary law
is asserted. An authenticated flat implementation remains unrecovered.

Target law, support, coordinates, topology and shared comparison geometry are
scientific decisions. Faithful algebra, identities, indexing and authentication
are mechanical invariants once those decisions are fixed.

## Accuracy region and tail policy

The study targets the central 99% interval of `log(ell_W) ~ Normal(0,0.5^2)`:
`[0.27584541747697255, 3.6252188241752448]`. Required tail diagnostics at
ell=0.15 and ell=5 are not formal certification points. No prior truncation or
silent rejection of tail proposals is approved.

The production policy to test later is to report posterior occupancy outside
the certified interval. Scientifically material posterior mass in uncertified
regions invalidates that run's numerical certification and requires expanded
certification and a rebuilt/refitted run. Never change meshes implicitly inside
an MCMC chain. The operational definition of scientifically material mass,
including Monte Carlo uncertainty and per-section reporting, remains a later
scientific decision; do not substitute an invented percentage now.

The interval is a certification target, not an existing guarantee. Finite grid
and probe checks support empirical claims only at those evaluations. A uniform
interval/location guarantee requires additional bounds or certification. Report
coverage honestly rather than describing the trial grid as a theorem.

## Staged numerical-study protocol

The [machine-readable specification](../../config/mesh/study-design.json),
[geometry enumeration](../mesh/study-geometries.csv) and
[range enumeration](../mesh/study-ranges.csv) define the experiment, not an
executable production run specification. Phase 0 is not implemented or executed.

| Factor | Explicit experimental levels |
| --- | --- |
| Inner h | ell_low / [2,4,8] = 0.13792270873848628, 0.06896135436924314, 0.03448067718462157 |
| Fine collar | ell_low/2 = 0.13792270873848628 |
| Grading | One rule: h(d)=min(h_inner+0.15*d, ell_high/4), with d outward from the fine collar; h_inner inside it |
| Buffer beyond collar | [1,2]*ell_high = 3.6252188241752448, 7.2504376483504895 |
| Central range evaluations | 17 log-spaced endpoint-inclusive points plus .3, .6, 1.65, 2.72: 21 unique points |
| Tail diagnostics | .15 and 5: 2 points, separate from certification |

One grading rule keeps the initial study bounded and isolates resolution/buffer
effects. The earlier two-rule, 108-geometry proposal is superseded; no second
grading factor is hidden in these counts. Experimental grading is fixed for this
study, while a production grading choice remains pending.

| Stage | New geometries | Central evaluations | Tail evaluations | Total evaluations |
| --- | ---: | ---: | ---: | ---: |
| Phase 0: S10__WT5, 3 h x 1 grading x 2 buffers | 6 | 126 | 12 | 138 |
| Phase 1: other 8 representative sections, same grid | 48 | 1008 | 96 | 1104 |
| Phases 0+1: 9-section panel, counting S10 once | 54 | 1134 | 108 | 1242 |
| Phase 2: remaining 10 sections x F finalists, 0<=F<=2 | 10F (at most 20) | 210F (at most 420) | 20F (at most 40) | 230F (at most 460) |
| Overall unique total | 54+10F (at most 74) | 1134+210F (at most 1554) | 108+20F (at most 148) | 1242+230F (at most 1702) |

Phase 0 uses S10, chosen before covariance evaluation for maximum span and a
persistent geometric gap. Evaluate its entire six-geometry grid and measure
construction, eigensolve, factorization, memory and continuum errors. Resource
exclusions remain explicit records. If assumptions fail materially, stop and
review; do not broaden execution or silently reduce the requested accuracy.
**Phase 0 must finish and be reviewed before Phase 1 is authorized.**

The representative panel is S01, S02, S04, S05, S07, S10, S12__Trem2_1,
S12__Trem2_5xFAD2 and S13, expanded to full registry IDs in the specification.
M3 selected six by deterministic feature coverage with both S12 sections forced,
then added the span, MST-gap and NN-density extremes before numerical results.
Reuse valid Phase-0 measurements in Phase 1; do not count S10 twice.

Phase 2 evaluates at most two Pareto finalists on the other ten sections. Each
finalist is one global (h, grading, buffer) tuple; no per-section tuning is
approved. If no acceptable candidate emerges, stop for a design amendment.
Rank only candidates completing the required representative evaluations;
resource-excluded candidates are incomplete, not successful. Report the full
Pareto frontier across accuracy, peak memory and measured timings, plus vertex
counts. Finalist selection requires review; do not choose solely by vertex count
or hide tradeoffs in a single PASS flag.

## Metrics and trial targets

For every candidate record independent analytic continuum comparison at fixed
deterministic probes, with unchanged probe identities across geometries. Use
boundary/interior/dense/sparse strata (256 probes, 64 per stratum), 20-NN density,
farthest-point coverage and raw-source-row tie breaks. Report outer-support and
persistent-gap boundary probes separately. The harness review must fix exact
overlap/fill rules and probe identities before candidate errors are observed.

Report unit-variance error, absolute correlation error and relative covariance
Frobenius error by range, distance bin and probe stratum. Use marginal-scale
absolute covariance errors when pairwise relative covariance is unstable.
Preferred trial targets are 0.02 for each primary metric (absolute correlation
error 0.02, not 2% relative correlation). **These are not canonical production
acceptance thresholds.** Show sensitivity and Pareto results before selecting
final thresholds from scientific and numerical evidence.

Also require resolution and buffer convergence; full-to-active marginal equality;
projector row sums, affine reconstruction and every-observation coverage;
triangle areas, angles and grading; support/topology metadata; unit-amplitude
log-range covariance and covariance-root derivative checks; full/active counts;
construction/eigensolve/factorization times; peak process-tree memory; and
projected sampler algebra cost. Record conditioning, residual maxima and both
absolute and relative derivative errors, with finite-difference step sensitivity.
Old proposal tolerances for secondary/discrete/derivative checks are context,
not automatically frozen acceptance constants. Trial angle/gradation targets,
probe details, environment and numerical tolerances require explicit harness
review before execution. No sampler amplitude law is adopted by these checks.

## Resources, authority and remaining work

Concurrency is one. The proposed study safety envelope is a 10 GiB total-process
memory ceiling and at least 8 GiB available headroom, including child processes
and library overhead. Check resources before work and monitor during it. Record
excluded/failed candidates with reasons; do not omit them or reinterpret them as
accuracy passes. Phase 0 replaces geometric memory/runtime guesses with measured
costs before broader authorization.

M3 resource estimates refer to the old two-grading proposal and are planning
evidence only, not promised vertex counts or runtimes for this revised study.
No production mesh builder, GP initialization, HPC work or sampler execution is
authorized. The next implementation is an **experimental Phase-0 study harness**.

Open: production h/grading/buffer and enclosure implementation, mesh environment
and determinism, final error thresholds, certified interval coverage, material
tail-occupancy criterion, physical units, anatomical interpretation of holes,
near-coincident-cell provenance, sampler amplitude authority and shared-geometry
flat implementation. No additional historical search is part of this decision.
