# BSFM sampler: bounded lineage and architecture recovery

Recovery baseline: `10cb6e27168aae7581831a6591089b4d88629c49`.
Recorded: 2026-11-02. The user accepted the bounded nomination and selected the
F/C production-overlay architecture in the
[architecture decision](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
This checkpoint contains documentation and source identities only. No historical
sampler source has been imported, no sampler environment built, and no sampler
or HPC execution performed as part of this gate.

## Evidence conventions and boundaries

Distinguish measured byte identity and verified source behavior from documented
historical claims, recorded execution evidence, mathematical inference and
explicit user selection. A hash authenticates bytes, not successful execution or
posterior convergence. The [source table](BSFM_SAMPLER_SOURCES.csv) records exact
external paths, byte sizes, SHA-256, evidence classes and inspected scope.

The bounded nomination read the existing mesh/SCTransform recovery references,
named manifests/indexes, statically traced imports, compared source bytes and
focused driver diffs, and read directly referenced launch/provenance records.
ZIP source members were read in memory; no source was extracted into this repo.
There was no drive-wide search, historical-code execution or HPC connection.
No additional search for missing LI results is authorized by this decision.

| Alias | Exact root |
| --- | --- |
| E | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CURRENT_20261014\bayesian_spatial_factor_model` |
| L | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_LI_KERNEL_GATE_20261014` |
| F | `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code` |
| C | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030\source_snapshot` |
| Z | `C:\Users\Data Viz\Downloads\BAYESIAN_SPATIAL_FACTOR_MCMC_20261014.zip` |

C sources have a `code/` prefix; Z members have the prefix
`bayesian_spatial_factor_model/`. All source line references below use F unless
another alias is stated. `F/../` refers to the containing October 26 package.
These are machine-local evidence locations, not canonical executable paths.

## Lineage and measured identities

| Driver at `sampler/run_c3full_fixed_profile_nuts.py` | Bytes | SHA-256 | Interpretation |
| --- | ---: | --- | --- |
| E and Z | 92894 | `3e81660c6d5e8772a35bfb2cc18a75988c26f6ac0fd7dd2c63e58a1d2859ac79` | Identical October 14 base snapshot. |
| L | 95650 | `658bc522d58eb084ed929f7194696376a163c8646ac0bf6bad8f38f13f9f557b` | LI transition experiment fork, not selected. |
| F and C/code | 94890 | `eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49` | Identical selected production-overlay driver. |

The lineage is October 14 base -> production retention/readaptation overlay ->
October 26 prepared four-stage-mesh package -> consolidation snapshot. L is a
separate experimental fork of the base. The 18 local dependencies shared by all
three drivers are byte-identical across E/L/F/C/Z. All 19 F runtime-closure hashes
match the F `../SOURCE_MANIFEST.json` and C `BUNDLE_MANIFEST.json` records.

The E-to-F diff adds retained `phi`, `delta`, `tau`, `W_cell`, `W_active` and
explicit checkpoint-only readaptation. It does not change the ordinary Gibbs
transition formulas. `PRODUCTION_CODE_MANIFEST.json:2-6` records both changes;
`PRODUCTION_OVERLAY_README.md:7-11` is older retention-only prose.

## Verified model and input boundaries

Let G be genes, N cells, C cell types and K factors. Input Y is G x N;
Lambda is C x G x K; eta is K x N. `cell_id` is length N, zero-based and
contiguous by type; `slocs` is N x 2. K comes from input `factors` in real-data
mode. The driver loads prepared Y unchanged and checks dimensions, finite Y and
nonempty contiguous type blocks (`driver:335-367`). It does not log, scale or
recenter Y. The canonical response and coordinate identities are governed by the
[response handoff](../decisions/MODELING_RESPONSE_HANDOFF.md).

The implemented likelihood is

\[
Y_{gi}=\sum_k\Lambda_{c(i),g,k}\eta_{ki}+\epsilon_{gi},\qquad
\epsilon_{gi}\sim N(0,\sigma_g^2).
\]

The noise is gene-specific and shared across cell types; observation weights
are fixed to one (`driver:493-496`; `c3_established_functions.py:2849-2869,
7193-7216`). No intercept or repeated latent-field centering is imposed by this
sampling path. The likelihood uses ordinary Gaussian algebra on supplied centered
Y; separate observable-covariance diagnostics apply a within-type centering
operator (`covariance_math.py:8-30`). These are distinct implemented behaviors.

For each factor,

\[
\eta_k\mid\alpha_k,\zeta_k,W_k\sim N\{0,\alpha_k^2[
\zeta_k\Phi(W_k)\Phi(W_k)^T+(1-\zeta_k)I]\}.
\]

Equivalently, eta is alpha times a smooth Gaussian feature field plus an
independent Gaussian nugget, weighted by sqrt(zeta) and sqrt(1-zeta).
Phi concatenates weighted cosine and sine features. The recorded L16 rule has
512 frequency nodes and 1024 feature columns, with exact-SE reference
`exp(-2 * squared_distance(W_i,W_j) / ell_eta^2)` and fixed ell_eta=0.14.
The finite-feature covariance is the implemented target; exact-SE agreement is
a separate diagnostic, not a certified identity. See
`fixed_splusu_dynamic_target.py:131-169,479-503` and
`provenance/INPUT_OUTPUT_SCHEMAS.json:404-459`.

Define B[:,g,k] = alpha[k] * Lambda[:,g,k] and
Omega_s = (1-s) I_C + s 11^T, with fixed s=0.20. Then

\[
B_{:gk}\mid\phi_{gk},\tau_k\sim N_C(0,\Omega_s/(\phi_{gk}\tau_k)),
\quad \tau_k=\prod_{j\leq k}\delta_j.
\]

Priors (Gamma uses shape/rate; inverse-Gamma uses shape/scale):

| Quantity | Implemented prior |
| --- | --- |
| phi[g,k] | Gamma(1.5, 1.5) |
| delta[1] | Gamma(2.1, 1) |
| delta[j>1] | Gamma(1.5, 1); driver overrides helper default 3.1 |
| log(alpha[k]) | Normal(log(0.7), variance 0.7) |
| zeta[k] | Beta(2, 2) |
| sigma2[g] | inverse-Gamma(2, 0.25 * population_variance(Y[g,:])) |

The data-calibrated noise-prior scale is computed once. Loading prior precision
contains alpha^2 * phi * tau. The collapsed alpha target retains both loading
normalization and quadratic terms (`driver:41-51,481-496`;
`c3_established_functions.py:3859-3913,6936-7026`;
`fixed_splusu_dynamic_target.py:231-235`).

### Warp and full-spectrum active marginal

Each factor has two direct coordinate fields, with shared geometry and
factor-specific range/amplitude. For n_A active vertices,

\[
W_{A,k}=\sigma_{W,k}L_A(\ell_{W,k})Z_k,\quad
W_{cell,k}=A_AW_{A,k},\quad Z_k\in\mathbb R^{n_A\times2}.
\]

The two columns have independent standard-normal prior coordinates; this does
not assert posterior independence. The direct-W adapter zeros the additive
spatial offset. Centered identity W is only the initialization.

\[
x_k=\log\ell_{W,k}\sim N(0,0.5^2),\quad
b_k=\log r_k\sim N(0,0.3^2),\quad
\sigma_{W,k}=\ell_{W,k}r_k/\sqrt{10}.
\]

The positive range prior is unbounded. Legacy output names `ell_U`, `sigma_U`
denote these W quantities. The Matérn/SPDE warp uses nu=5, FEM order 6,
kappa=sqrt(40)/ell_W and full generalized eigenbasis U with U^T C U=I.
Writing G_0=C,

\[
q_m(\ell_W)=\frac1{20\pi}\sum_{j=0}^6{6\choose j}
\kappa^{2-2j}(U^TG_jU)_{mm},\quad
\Sigma_A=U_A\operatorname{diag}(q^{-1})U_A^T=L_AL_A^T.
\]

Positive-diagonal QR gives the active root using all full-mesh modes. Inactive
vertices are marginalized, not zero-fixed or removed by slicing precision.
The raw-Q variance is not renormalized with range. See
`generate_splusu_phase1.py:28-35`, `spectral_live_range_whitening.py:40-162,166-223`,
`active_marginal_whitening.py:14-59`, `direct_w_dynamic_target.py:16-40`.

Warp amplitude controls distances in the factor kernel. Response loading
amplitude is alpha*Lambda. The PX move redraws alpha from its prior and rescales
Lambda and eta to preserve B, eta/alpha, fitted Y and alpha^2*q(Lambda)
(`driver:182-230`). There is no truth-based sign/label adjustment in real-data
transitions; real-data saved permutation is identity (`driver:1317-1321`).
Random factor visitation does not relabel factors. No authenticated flat-fit
arm with shared geometry was recovered.

## Exact Gibbs chronology

The selected invocation has adaptive MGP, direct W, live warp hypers, split-E,
fixed ell_eta and no containment penalty or live outer-range experiment.

1. Repeat three times: draw Lambda jointly across types/factors per gene;
   draw all eta jointly; draw gene sigma2.
2. Draw phi; draw delta sequentially and recompute cumulative tau.
3. Perform the invariant PX-alpha refresh and update its stored log coordinate.
4. Randomly permute factor visitation.
5. For each factor, rebuild current leave-factor-out residual/sufficient
   statistics and loading penalty. Integrate eta_k out of the factor target.
6. NUTS jointly updates log-alpha, logit-zeta and all zW with x,b fixed.
7. Map to physical W_A. NUTS updates x=log-ell and b=log-r at fixed W_A,
   including the two-coordinate GP determinant, quadratic and hyperprior terms.
8. Rewhiten the same W_A under the new hypers. Draw eta_k once, then refresh
   fitted Y before the next factor. There is no intermediate eta draw.

Sigma_W follows its coupled formula, not an independent third hyperparameter.
At fixed W, alpha and zeta the collapsed likelihood does not depend on x,b.
The physical-W invariance threshold is 2e-8. Joint eta uses Gaussian
perturb-and-solve PCG with posterior-metric RMS error bound <=1e-10 and maximum
80 iterations; failure is fatal. This is a tolerance-controlled numerical draw.
Sources: `driver:1113-1270`, `full_split.py:19-87`,
`centered_hyper_target_qr.py:38-89`, `joint_eta_pcg.py:152-262`.

Warmup holds outside-Gibbs sufficient statistics fixed for each factor while
alternating split moves. It adapts two diagonal mass blocks/two step sizes,
initialized at .01, using the BlackJAX window schedule. Each factor endpoint and
its eta redraw are propagated to subsequent factors and retained. Tuning freezes
after warmup (`driver:671-734,924-986`; `full_split.py:58-87`).

## Checkpoints, outputs and boundaries

The historical numerical input is `OBSERVATIONS.npz` containing Y, cell_id,
slocs, factors, active_indices, A_active and mesh_vertices. FEM inputs are
`fem_C.mtx`, `fem_g1.mtx` through `fem_g6.mtx` and `A_proj.mtx`. A frozen TQFF
rule supplies frequencies/weights and provenance. Coordinate identities and
normalization must agree with the [canonical mesh](../mesh/OCTOBER26_CANONICALIZATION.md).

GPINIT supplies only Lam_seed[C,G,K] and eta_seed[K,N]. Initial alpha is
max(std(eta_seed),1e-3), then PX preserves their fitted signal. The historical
driver checks shapes, not all gene/cell hashes; preparation/wrappers carry the
identity linkage. GPINIT does not replace Y or define the posterior target.
See `driver:468-516` and the [canonical initializer](../initialization/C3_GP_SVD.md).

`POST_WARMUP_CHECKPOINT.npz` precedes the first sweep.
`LATEST_CHECKPOINT.npz` is written by temporary NPZ plus os.replace after every
complete sweep. It contains Lambda, eta, alpha, zeta, ell_eta, ell_U, sigma_U,
sigma2, positions, phi/delta/tau, field/hyper step sizes, inverse masses, JAX
master key, both NumPy Generator states and global NumPy state, spectral chart,
contract and local progress. Contract equality checks inputs, rule, mesh and
selected settings (`restart_state.py:63-126`; `driver:1107-1112,1439-1446`).

Normal complete-checkpoint restart restores state, RNG, spectral chart and frozen
tuning; warmup must be zero. Explicit readaptation-on-resume permits new window
adaptation from that checkpoint and retains the new endpoint. Local sweep numbers
restart; previous draw archives are not merged automatically. Legacy incomplete
checkpoint conversion is not selected. Historical checkpoint contracts do not
authenticate a complete software/environment identity.

Draw storage excludes settling and follows configured save cadence plus the final
sweep. Arrays include sweep, Lambda, eta, alpha, zeta, ell_eta, ell_U, sigma_U,
sigma2, phi/delta/tau, W_cell, W_active, positions and permutation. Scalar/factor
traces record every sweep. Diagnostics include acceptance, divergences,
leapfrogs, W invariance, PCG bounds, PX checks, warp spans and TQFF fidelity.
No cadence or run length is selected here (`driver:1271-1345,1395-1446`).

## Historical execution evidence and conflicting specifications

| Record | Evidence class and limit |
| --- | --- |
| E VALIDATION.json | Recorded 10 covariance tests and CPU split algebra/gradient/context/replay pass; toy warmup had divergences. Not a mixing benchmark. |
| E provenance/RECORDED_COMMAND.json and SOURCE_SNAPSHOT.json | Recorded simulation invocation/source identities; no completed-chain certificate recovered here. |
| F PRODUCTION_LAUNCH_CONTRACT.json:30-39 | Historical claims of passing readaptation/K25 pilot jobs, zero pilot production divergences and reconstruction checks; underlying pilot outputs not inspected. |
| F ../WORK_LOG_20261026.txt:53-60 | Recorded successful 19-section CPU preparation/GPINIT and split regression; cloud VM explicitly not started. |
| C PACKAGE_RESULT.json | READY_FOR_CLOUD_GPU_PREFLIGHT; GPU_smoke_run=false. |
| C ../bsfm_cleanup_audit_20261030/old_campaign_jobs.tsv | Historical scheduler capture: 15 completed adaptation records; production records: 6 failed, 4 node-failed, 5 pending, 3 running, none completed. Older K20/75% mesh campaign; no F campaign certification. |

All these are preserved historical records, not newly observed cluster state.
There is no claim of a completed or converged historical F campaign.

| Configuration source | Historical values only; not selected run policy |
| --- | --- |
| CLI defaults | warmup 50, sweeps 40, settling 0; several prior-center defaults differ from active direct-W flags |
| E CURRENT_CONFIGURATION.json | K5 simulation; warmup 100, settling 50, production 300, save every 5 |
| F ../cloud_run.py:32-46 | K20 prepared input, one chain, warmup 100/block, settling 50, production 100, save every 5; seed 2026102700+section_index |
| Inherited K25 contract/wrappers | four chains; bridge then readaptation; settling 100, production 1000, save every 5; seed 2026102400+100*section_index+chain_index |

The bridge wrapper actually requests 101 sweeps with 100 settling, retaining a
final endpoint (`production/run_adaptation_bridge_chain.sh:49`). No wrapper is
made canonical by selecting the sampler architecture.

## Experimental branches and unresolved items

L tests ordinary prior ESS, empirical LI-ESS on zW/field/warp/full blocks,
LI-whitened NUTS, Fisher ESS and a conditional Fisher variant. Empirical references
use warmup covariance shrunk 20% toward its diagonal with eigenvalue flooring.
Fisher variants use Fisher-plus-prior precision; the conditional variant freezes
a physical-W anchor and rebuilds the Gaussian reference from current conditioning
variables, holding it fixed within each ESS move. ESS uses log target minus log
reference. Centered variants retain fixed-W hyper NUTS and one subsequent eta
redraw. LI checkpoint restart is explicitly disabled.

Sources: `L/EXPERIMENT_DESIGN.md`, `L/sampler/li_split.py:57-139,187-327,329-471`,
`L/sampler/quadrature_fisher_reference.py:20-118`. Wrappers describe smoke,
two-chain screening and four-chain matched comparisons. The local results and
analysis output tables were absent during nomination. ESS/second improvement,
R-hat improvement and historical promotion/rejection were not established.
These branches are now explicitly noncanonical by user decision, without an
invented empirical performance conclusion.

Remaining contradictions/limits:

- CURRENT_MODEL_AND_UPDATES.txt:4-6 says the driver centers Y; source does not.
- The inherited K5/K25/K20 run descriptions conflict; runtime flags and input K
  determine behavior. No run lengths, chain count or K are selected here.
- The overlay README omits readaptation. The manifest and diff include it.
- The sampler can emit COMPLETE_WITH_FIDELITY_WARNINGS; an older production
  wrapper accepts only PASS/REVIEW_REQUIRED. The cloud wrapper uses exit status
  and retained-draw validation. Canonical completion semantics need explicit
  implementation, without hiding numerical or fidelity warnings.
- Projected covariance diagnostics and the actual likelihood are distinct;
  preserve the implemented target rather than silently changing it.
- Flat/deep shared-geometry fitting and historical LI performance remain
  unrecovered. Neither is required to select the nominated deep sampler.
- Historical environment records list Python 3.11.14, JAX/jaxlib 0.7.0,
  BlackJAX 1.3, NumPy 2.1.3, SciPy 1.14.1, pandas 2.2.3 and matplotlib 3.10.8.
  HPC wrappers name CUDA 12.3/GCC 12.2.0. requirements-core.txt explicitly is
  not a full transitive or GPU lock; CUDA plugin/cuDNN/driver/build identities
  remain incomplete. No environment is built or selected here.
- Optional legacy polyagamma, shapely, jaxopt, R/INLA and full_fisher_metric
  branches are outside the active Gaussian path. Import-time pandas/matplotlib
  dependencies partly reflect monolithic helpers, not new scientific requirements.

The next port must obey the bounded function-extraction and module organization
in the [architecture decision](../decisions/BSFM_SAMPLER_ARCHITECTURE.md).
