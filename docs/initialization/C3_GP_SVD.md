# Canonical C3 GP-smooth-to-SVD cold-start initialization

Baseline: `391041a4ff0b7d0d20c7c66c039744ee3c87726c`. The user accepted the S10
reproduction as numerically equivalent for a cold-start initializer on
2026-11-02, explicitly not byte-exact. The initializer supplies starting values;
the sampler must consume its immutable modeling response separately. No
all-section execution or sampler implementation is approved by this checkpoint.

## Authenticated lineage

P = `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_19_SECTION_PRODUCTION_20261024`.
F = `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1`.
P `sampler/build_gpinit_from_truth_npz.py` and F
`code/sampler/build_gpinit_from_truth_npz.py` are byte-identical: 8,433 bytes,
SHA-256 `f5b1545072c462cf772cd3caf44a398da8cf5558b4a2dd3133922c8cd8143f94`.
The source docstring attributes the recipe to September C3 and describes an
adaptation from CSV to NPZ. That is a source documentation claim, not an
independently recovered September implementation.

F `prepare_cpu.sh:6-16` selects the section by zero-based position in
`SECTIONS.json`, uses the HPC Python `/work/abussing/arka_trying_gpu_again/env/bin/python3`,
sets BLAS/OpenMP threads to four, and supplies K=20, nfit=250 and seed
`2026102600 + INDEX`. S10 is index 10: **2026102610**. These are authenticated
wrapper settings; the GPINIT certificate does not independently attest the seed.
Wrapper SHA-256: `2713f6f120fff645f4161d487f4ba6240e29df812cb8b21de17df9df376af7d8`.
Section-list SHA-256: `0bb354335d887ed10c2f1c694ed17a2ad85f6a1a84fa368de2bcd78d05b386b9`.

K and nfit remain explicit arguments. Historical full-cell certificates use
K=25, while retained-cell records use K=20; neither fixes the future model size.
See the [B3 ledger](../recovery/SCTRANSFORM_B3_SECTIONS.csv).

## Exact recovered recipe

Line references below refer to the authenticated 214-line builder, not unrelated
sampler code. No historical implementation was imported or executed.

| Lines | Implemented behavior preserved in the port |
| --- | --- |
| 49-66 | Read Y (genes × cells), slocs (cells × 2), integer type codes. Copy Y as float64 and subtract arithmetic within-type gene means from this private fit copy only. No changed response is exported. |
| 69,79-82 | One `RandomState(seed)`; enumerate integer types in increasing order. Draw min(nfit, type count) indices without replacement, retaining RNG order. One shared subset per type serves every gene. |
| 84-96 | Constant(1; bounds .01–100) × isotropic Matérn(length .3; bounds .02–3; nu=2.5) + WhiteKernel(.5; bounds .001–100). normalize_y=True, alpha=1e-6, zero optimizer restarts. Predict each type/gene field at **all** supplied modeled-cell locations, including other types. |
| 97-118 | Record fitted length scales and predicted-field variances. Variance-weighted median length scale, ordinary median if total weight is zero, .3 if none recovered. Missing diagnostic length-scale extraction leaves NaN; GP fit/prediction errors themselves are not caught. |
| 120-132 | Stack fields in type-major/gene-minor order as (C×G) × N. Center every row over all N prediction locations. Full economy NumPy SVD; take first K components. Normalize each loading column over all C×G entries, floor 1e-12; transfer its norm into eta. |
| 134-156 | Continue the same RNG to choose min(400,N) cells for diagnostic factor GPs. Their kernel uses length bounds .02–1.5, initial noise .1, noise bounds .001–10. Extract diagnostic ranges, falling back to theta prior summary only on extraction failure; clip to .02–1.5. Fit errors still propagate. |
| 158-177 | Compute reconstruction/correlations. Export Lam_seed(C,G,K), eta_seed(K,N), theta_prior_mu, field_ls/theta_seed(K), first min(20,C×G,N) singular values and two correlations. No Y or trained per-gene GP objects exported. |

The implicit optimizer in the pinned library is L-BFGS-B on negative log
marginal likelihood; zero restarts still makes one optimization from the kernel
initial values. Library target normalization is undone for predictions. The
port makes this optimizer default explicit. See the
[official scikit-learn 1.4.2 source](https://github.com/scikit-learn/scikit-learn/blob/1.4.2/sklearn/gaussian_process/_gpr.py).

There is **no explicit SVD sign convention** beyond the numerical backend's
returned signs. The port preserves this; it does not introduce `svd_flip` or
another gauge. Same-environment determinism is tested; cross-platform sign
identity is not guaranteed. Loading columns have unit Frobenius norm across
type/gene entries (apart from the source's floor for degenerate columns), with
amplitude in eta. Scale allocation is therefore not left wholly unspecified.
The extra factor ranges are diagnostic; no sampler-consumer code was inspected
or ported in this gate.

The source globally suppresses warnings. The port captures/counts warnings
locally for review instead, preserving fit behavior and propagating failures.
It validates identities/parameters earlier, scopes thread limits, and adds
hashes and pickle-free readback. It does not change kernels, GP optimizers,
subsample selection, field centering, SVD or amplitude allocation.

## Proposed interface and contract

One module: [`bsfm.initialization.gp_svd`](../../src/bsfm/initialization/gp_svd.py).
One [configuration](../../config/initialization/c3-gp-svd.json); parameters K,
nfit and seed are required by the CLI. Input is an NPZ with the three numerical
arrays plus gene_names, cell_names, source_row_indices and cell_type_names.
All arrays are loaded with allow_pickle=False. IDs must be unique, type codes
contiguous/nonempty, and dimensions/finite values valid.

The separate `bsfm.gpinit-input.v1` JSON contract contains response=
`final_centered_Y`, source_sha256 and an ordered logical hash for each required
array. Logical hashes cover shape, dtype and C-order little-endian numeric
bytes; string arrays use ordered UTF-8 JSON. Loading rejects hash/order changes.
The scalar type codes are not cell identifiers: the latter have a separate axis.

The caller supplies reference locations with an explicit coordinate-transform
description. No coordinate transformation occurs inside GP fitting. Historical
S10 uses the glial minimum/max-span normalized coordinates already in its NPZ,
not raw source-native distances. This gate does not implement an HDF5 response
adapter or reinterpret physical units. Such an adapter must preserve Y exactly
and supply the approved reference-coordinate representation.

CLI: `python -B -m bsfm.initialization.gp_svd --input <observations.npz>
--contract <input-contract.json> --output <fresh-directory> --factors <K>
--nfit <nfit> --seed <seed>`. It refuses an existing output directory. Outputs
are gpinit.npz plus certificate.json containing configuration/code/input hashes,
all output logical hashes, full fitting-point indices, measured diagnostics,
warnings and runtime/package provenance. Saved arrays are reopened without
pickle and compared exactly before the certificate records pass. This is a
single-run review interface, not a resumable all-section production launcher.

## Bounded S10 result

The local F gpinit directory is empty. The exact reference was recovered from
the already indexed READY archive, not a new filesystem search:
`D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1_READY.tar.gz`.
Its size is 98,111,074 bytes; SHA-256
`4458f784c8e760893c5fcd620f8ec74f40d9f504a0fa7d5fcbda9f29fe600f07`.
Only the exact S10 gpinit.npz and CERTIFICATE.json members were read from it.
Their hashes match the committed package manifest:

- GPINIT: 765,813 bytes; `e912139820413de0e4f5365cd0d8eb70512b71a9f31c32bd042d565b04f044fc`.
- Certificate: 2,029 bytes; `f7126f014ca300279aa3d43d235b9278fcf6048a237c88b8c193dbcb3c85fa12`.
- Observation NPZ: 630,227 bytes; `c6356cc2da031e441c1955e831308cc1c3f87ac391845fa40feede1ba97ba4fc`.

The single S10 fit used 4,712 cells, 91 genes, type counts 498/1669/2545,
K=20 and nfit=250. The recovered seed determines 750 fitting locations and a
400-cell diagnostic subset. The historical artifact did not export its fitting
indices or full smoothed fields, so those cannot be directly compared; the
new certificate records them for future authentication.

| Measurement | Result |
| --- | --- |
| Local fitting runtime | 53.5693 seconds (historical certificate: 80.8928 seconds) |
| Input numerical recentering maximum | 7.106736068435531e-15, exactly matching the certificate |
| Predicted-field mean maximum after centering | 3.0158859752126495e-17 |
| Loading orthogonality maximum error | 1.1783109210572462e-15 |
| Eta mean maximum | 1.960325883888222e-17 |
| Largest singular-value difference | 2.9410946567054452e-8 |
| Loading maximum absolute difference | 2.1545562227213988e-7 |
| Eta maximum absolute difference | 2.188970268934831e-8 |
| Reconstructed-field relative Frobenius difference | 5.4445910829792996e-8 |
| Sign comparisons | All 20 agree; no sign correction applied to outputs |
| File/logical byte identity | Not equal |

The predeclared diagnostic allclose check (rtol=1e-8, atol=1e-10) passes six
output fields but **fails Lam_seed and eta_seed**. No tolerance was relaxed and
no fit was retried or tuned to obtain agreement. This is close measured
cross-platform agreement, not exact reproduction. The subsequent explicit user
decision accepts it under the representation-aware cold-start criterion below.
The original strict failures remain in the byte-unchanged comparison receipt;
no tolerance was changed post hoc to claim exact equality. Platform/backend
differences are a plausible explanation, not an established causal diagnosis.
The reviewed fitting source remains byte-identical to the S10 execution source.

## Accepted historical regression policy

The [frozen comparison policy](../../config/initialization/historical-regression.json)
requires, specifically for historical cross-platform cold-start regression:

- `||Lam_new eta_new - Lam_old eta_old||_F / ||Lam_old eta_old||_F <= 1e-6`;
- `||s_new - s_old||_2 / ||s_old||_2 <= 1e-8` for the stored leading singular values;
- identical dimensions, ordering and input hashes;
- the same K, nfit, seed, fitting algorithm and kernel configuration.

This is a user-approved cold-start equivalence criterion, not a general scientific
accuracy threshold. Same-environment repeated fits and saved-artifact readback
continue to require exact equality. No fitting tolerances, kernels, optimization
settings or SVD conventions were changed. The configuration's acceptance status
label is the only change from the [executed configuration](audits/S10_20261102/executed-config.json).

The [saved-array comparison](audits/S10_20261102/representation-comparison.json)
was computed without fitting anything. Its
[reproduction script](audits/S10_20261102/compare_saved.py) authenticates the input,
archived reference, output, certificates, builder and configuration identities.

| Representation-aware diagnostic | S10 result |
| --- | --- |
| Reconstructed-field relative Frobenius error | 5.4445910829792996e-8; passes 1e-6 |
| Singular-value relative L2 error | 3.2739333739081037e-10; passes 1e-8 |
| Loading projector relative Frobenius discrepancy | 1.1811217533852415e-7 |
| Largest loading principal angle | 3.734448071639509e-7 radians |
| Eta row-space projector relative Frobenius discrepancy | 9.452456966595415e-9 |
| Largest eta row-space principal angle | 2.956110223620899e-8 radians |
| Rank and sign diagnostics | Both spaces rank 20 in each artifact; all 20 signs agree |

Projector discrepancies use orthonormal QR bases and residual projections,
avoiding cancellation near equality and avoiding a dense 4,712-by-4,712 projector.
They and the principal angles are diagnostics, not extra acceptance thresholds.
Historical output axes are linked by the same authenticated input bytes and
preserved builder ordering; the old seeds do not contain independent axis labels.
The seed is authenticated from the wrapper formula, not a historical runtime
certificate field. These provenance limits remain explicit.

GPINIT affects starting values, not the posterior target. Lam/eta are
gauge-dependent factorization coordinates: compensating sign or scale changes
can preserve their product. This statement does not assert symmetry of every
future BSFM prior or constraint. Correct MCMC must not depend on exact historical
seed bits; initialization can affect finite-run mixing and convergence, which
still require assessment. The diagnostic GPINIT ranges do not silently set
posterior-target parameters. K remains configurable and is not selected here.

All 13 focused tests pass, including an actual small spatial-signal example,
repeated fits, type-specific fit inputs/all-cell predictions, parameter and
identity corruption, unmodified Y, inherited SVD signs, loading gauge and saved
readback. Acceptance also reruns all 104 existing Python tests (with R/fmesher
integration) in the accepted mesh Python, seven R validation cases, the existing
four-fit SCTransform synthetic repeat gate and saved-model readback in the
accepted SCT environment. See the [acceptance checks](audits/S10_20261102/acceptance.json)
for commands, outcomes and hashes. No S10 refit, other-section GP run, sampler,
NUTS, factor-count comparison, holdout experiment or HPC connection occurred.

Machine-local review artifacts:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\gpinit_S10_20261102`.
They are generated from uncommitted review code, not production artifacts.
See the [small comparison receipt](audits/S10_20261102/comparison.json) and
[environment lock](../../environment/gpinit/README.md).
