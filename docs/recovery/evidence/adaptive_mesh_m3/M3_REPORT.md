# M3 temporary scientific design report

**Status: proposal for review; no design frozen, repository edits, FEM generation, or study execution.**

Measured baseline: `35a22212528d24daba218e48da54a9f8ee8f0c76`; main and origin/main agree; working tree clean.

Measured inputs: canonical SCTransform v2 run manifest and all 19 section manifests, coordinate and identity datasets only. Semantic hashes and all/model joins passed. Whole response.h5 hashes were not reread because that would read expression payload bytes. No raw-H5AD access was necessary. No historical search or HPC access occurred.

All distances and areas below are source_native and source_native squared. Axis order is center_y, center_x. No physical calibration is asserted.

## Geometry methods and limitations

Measured pooled all-cell nearest-neighbor median d0 = 14.8649161447464. Radius graph grid: 1,2,4,8,16,32 times d0. Components were computed from a Euclidean MST on diagnostic Delaunay edges (not a production mesh or FEM). Direct radius-graph checks at 8*d0 independently matched all component counts and size multisets for all 38 populations.

Empty-region diagnostics use the bounded complement of a raster union of disks of radii 2,4,8,16*d0. Grid spacing d0/2; reported large-hole area threshold 64*d0^2. These predeclared thresholds are diagnostics, not selected anatomy or meshing thresholds. S02/S10/S16 coarse persistent holes were rechecked at d0/4 and two grid phases. Exact component-size multisets, hole areas and bounding boxes are in audit.json.

## Complete coordinate table (measured)

NN columns are q10/q50/q90/q99. Spans are center_y,center_x. A=all cells, G=MIC/AST/OGC.

| Section | Population | N | Spans | Max span | NN quantiles |
|---|---|---:|---|---:|---|
| S00__Trem2_5xFAD4 | all | 20719 | 4206.262, 6698.632 | 6698.632 | 8.315/15.226/28.119/43.241 |
| S00__Trem2_5xFAD4 | glial | 9451 | 4179.370, 6680.866 | 6680.866 | 9.967/22.175/41.394/64.308 |
| S01__5xFAD4 | all | 24087 | 6671.144, 6654.899 | 6671.144 | 8.439/15.285/27.764/42.959 |
| S01__5xFAD4 | glial | 11938 | 6621.896, 6654.305 | 6654.305 | 9.565/20.769/39.080/63.058 |
| S02__Trem2_4 | all | 26716 | 6021.665, 6993.828 | 6993.828 | 6.548/14.293/27.268/43.753 |
| S02__Trem2_4 | glial | 8949 | 6013.889, 6987.996 | 6987.996 | 8.131/23.954/46.893/74.409 |
| S03__Trem2_5xFAD3 | all | 22868 | 4646.028, 6828.097 | 6828.097 | 8.448/15.271/28.372/43.168 |
| S03__Trem2_5xFAD3 | glial | 10557 | 4643.976, 6776.581 | 6776.581 | 9.299/20.983/42.222/68.642 |
| S04__WT3 | all | 17863 | 5652.390, 6023.406 | 6023.406 | 8.678/16.326/30.747/46.879 |
| S04__WT3 | glial | 8308 | 5593.206, 6014.010 | 6014.010 | 10.062/23.222/44.698/70.294 |
| S05__Trem2_3 | all | 22539 | 5610.119, 6031.096 | 6031.096 | 0.056/12.057/27.498/43.058 |
| S05__Trem2_3 | glial | 10128 | 5597.267, 6009.118 | 6009.118 | 0.054/15.991/41.754/67.609 |
| S06__5xFAD3 | all | 22965 | 5239.258, 7249.781 | 7249.781 | 8.481/15.725/29.398/45.196 |
| S06__5xFAD3 | glial | 11387 | 5161.660, 7231.151 | 7231.151 | 9.538/20.853/41.864/68.064 |
| S07__Trem2_5xFAD5 | all | 18594 | 4460.512, 6678.134 | 6678.134 | 8.821/15.336/27.995/43.514 |
| S07__Trem2_5xFAD5 | glial | 8054 | 4459.108, 6673.382 | 6673.382 | 10.401/21.923/42.386/71.538 |
| S08__5xFAD5 | all | 19034 | 5208.004, 6673.733 | 6673.733 | 9.104/16.022/29.945/46.363 |
| S08__5xFAD5 | glial | 8609 | 5175.496, 6619.463 | 6619.463 | 10.807/22.421/43.652/72.744 |
| S09__Trem2_5 | all | 23223 | 5203.343, 6478.864 | 6478.864 | 8.702/15.585/28.658/45.033 |
| S09__Trem2_5 | glial | 9015 | 5202.263, 6472.600 | 6472.600 | 10.528/24.166/46.497/71.580 |
| S10__WT5 | all | 25307 | 5776.147, 7610.556 | 7610.556 | 8.898/15.885/29.104/44.709 |
| S10__WT5 | glial | 9422 | 5716.747, 7551.696 | 7551.696 | 11.039/24.930/47.626/76.075 |
| S11__Trem2_5xFAD1 | all | 23598 | 5169.414, 6532.121 | 6532.121 | 8.442/15.657/28.787/44.151 |
| S11__Trem2_5xFAD1 | glial | 10913 | 5148.138, 6447.827 | 6447.827 | 10.051/22.059/42.544/66.221 |
| S12__Trem2_1 | all | 28532 | 6020.844, 6645.733 | 6645.733 | 0.077/13.137/25.957/41.248 |
| S12__Trem2_1 | glial | 11650 | 6018.738, 6630.451 | 6630.451 | 0.076/19.202/40.951/66.962 |
| S12__Trem2_5xFAD2 | all | 27741 | 5471.555, 6436.917 | 6436.917 | 0.077/13.417/27.521/42.285 |
| S12__Trem2_5xFAD2 | glial | 13485 | 5471.501, 6417.477 | 6417.477 | 0.077/18.668/39.258/61.977 |
| S13__Trem2_2 | all | 14282 | 3584.747, 4601.027 | 4601.027 | 0.078/13.100/25.693/42.503 |
| S13__Trem2_2 | glial | 5055 | 3584.747, 4597.679 | 4597.679 | 0.077/20.383/44.618/67.338 |
| S14__WT1 | all | 24291 | 5612.675, 6067.358 | 6067.358 | 8.257/15.239/28.022/43.631 |
| S14__WT1 | glial | 9424 | 5612.675, 6066.278 | 6066.278 | 10.219/23.599/44.857/69.312 |
| S15__5xFAD1 | all | 23957 | 5407.013, 5638.705 | 5638.705 | 8.164/14.369/26.255/40.471 |
| S15__5xFAD1 | glial | 10875 | 5399.777, 5638.597 | 5638.597 | 9.273/20.408/38.815/62.050 |
| S16__WT2 | all | 21030 | 5641.567, 6014.163 | 6014.163 | 8.425/15.444/28.832/45.294 |
| S16__WT2 | glial | 8200 | 5641.567, 6014.163 | 6014.163 | 10.746/24.430/45.838/72.430 |
| S17__5xFAD2 | all | 25448 | 5099.627, 6030.678 | 6030.678 | 8.267/14.567/26.444/41.343 |
| S17__5xFAD2 | glial | 11680 | 5065.985, 5844.109 | 5844.109 | 9.301/20.126/38.912/61.349 |

## Complete topology table (measured)

Component counts follow radii [1,2,4,8,16,32]*d0. Hole counts follow disk radii [2,4,8,16]*d0. The size column lists every component at radius 8*d0; full histograms at every radius are in audit.json.

| Section | Population | Component counts | Sizes at 8*d0 | Large-hole counts |
|---|---|---|---|---|
| S00__Trem2_5xFAD4 | all | 14243,3720,33,1,1,1 | 20719 | 21,2,0,0 |
| S00__Trem2_5xFAD4 | glial | 8112,4586,361,2,1,1 | 9450, 1 | 27,4,0,0 |
| S01__5xFAD4 | all | 16662,4184,52,6,4,4 | 24066, 17, 1 x 4 | 13,0,0,0 |
| S01__5xFAD4 | glial | 9973,5246,395,9,4,4 | 11831, 74, 16, 12, 1 x 5 | 44,3,0,0 |
| S02__Trem2_4 | all | 17316,4169,58,1,1,1 | 26716 | 27,4,1,1 |
| S02__Trem2_4 | glial | 7734,5089,767,5,1,1 | 8934, 9, 4, 1 x 2 | 26,15,2,1 |
| S03__Trem2_5xFAD3 | all | 15964,4394,37,1,1,1 | 22868 | 21,4,1,0 |
| S03__Trem2_5xFAD3 | glial | 8793,4887,520,13,2,1 | 10544, 2, 1 x 11 | 32,10,3,0 |
| S04__WT3 | all | 13029,4443,86,1,1,1 | 17863 | 29,1,1,0 |
| S04__WT3 | glial | 7194,4381,563,3,1,1 | 8306, 1 x 2 | 19,16,1,1 |
| S05__Trem2_3 | all | 14005,4453,37,1,1,1 | 22539 | 27,1,0,0 |
| S05__Trem2_3 | glial | 7403,4599,586,5,1,1 | 10122, 2 x 2, 1 x 2 | 25,10,1,0 |
| S06__5xFAD3 | all | 16323,4931,67,1,1,1 | 22965 | 28,1,0,0 |
| S06__5xFAD3 | glial | 9445,5132,571,3,1,1 | 11383, 3, 1 | 28,18,1,0 |
| S07__Trem2_5xFAD5 | all | 12873,3238,37,4,1,1 | 18530, 61, 2, 1 | 18,2,2,0 |
| S07__Trem2_5xFAD5 | glial | 6930,3821,428,7,3,1 | 8047, 2, 1 x 5 | 18,6,2,1 |
| S08__5xFAD5 | all | 13553,4147,69,2,1,1 | 19031, 3 | 32,3,0,0 |
| S08__5xFAD5 | glial | 7462,4290,497,23,2,1 | 8514, 49, 6, 5, 4 x 2, 3 x 2, 2 x 6, 1 x 9 | 24,8,1,0 |
| S09__Trem2_5 | all | 16315,4471,44,2,1,1 | 23214, 9 | 30,1,0,0 |
| S09__Trem2_5 | glial | 7918,5009,686,8,1,1 | 8990, 10, 4 x 2, 3, 2, 1 x 2 | 32,16,0,0 |
| S10__WT5 | all | 18135,5056,73,1,1,1 | 25307 | 31,1,1,1 |
| S10__WT5 | glial | 8380,5403,871,7,1,1 | 9405, 6, 4, 3, 2, 1 x 2 | 35,26,1,1 |
| S11__Trem2_5xFAD1 | all | 16687,4904,63,4,1,1 | 23594, 2, 1 x 2 | 22,2,0,0 |
| S11__Trem2_5xFAD1 | glial | 9345,5461,523,2,1,1 | 10912, 1 | 36,8,1,0 |
| S12__Trem2_1 | all | 17623,4131,58,4,1,1 | 28517, 7, 5, 3 | 21,5,0,0 |
| S12__Trem2_1 | glial | 9143,5286,605,4,1,1 | 11640, 6, 2 x 2 | 28,15,1,0 |
| S12__Trem2_5xFAD2 | all | 17708,4894,38,4,1,1 | 27738, 1 x 3 | 27,0,0,0 |
| S12__Trem2_5xFAD2 | glial | 10493,5822,469,4,1,1 | 13478, 5, 1 x 2 | 43,4,0,0 |
| S13__Trem2_2 | all | 8625,1945,26,1,1,1 | 14282 | 15,1,0,0 |
| S13__Trem2_2 | glial | 4031,2519,363,1,1,1 | 5055 | 7,4,0,0 |
| S14__WT1 | all | 16695,4155,62,2,1,1 | 24289, 2 | 21,7,1,0 |
| S14__WT1 | glial | 8259,5042,591,12,3,1 | 9298, 102, 13, 3, 1 x 8 | 26,12,1,0 |
| S15__5xFAD1 | all | 15574,3141,36,2,1,1 | 23955, 2 | 15,0,0,0 |
| S15__5xFAD1 | glial | 8978,4559,333,4,1,1 | 10869, 3, 2, 1 | 24,4,0,0 |
| S16__WT2 | all | 14608,4032,58,4,1,1 | 21027, 1 x 3 | 25,6,3,1 |
| S16__WT2 | glial | 7286,4576,599,6,1,1 | 8188, 5, 3, 2, 1 x 2 | 22,15,4,3 |
| S17__5xFAD2 | all | 16771,3434,44,2,1,1 | 25447, 1 | 20,3,0,0 |
| S17__5xFAD2 | glial | 9630,5000,364,2,1,1 | 11679, 1 | 35,6,0,0 |

## Interpretation and proposals

Measured: 432,794 all cells and 187,100 glial cells. All-cell hull areas exceed glial hulls by 0.344%-2.999%; 0.213%-1.855% of all cells lie outside the corresponding glial hull. Disk-union coverage increases much more at local scales (29.3%-53.9% at 2*d0, 3.6%-11.5% at 4*d0). These are geometric support proxies, not authenticated anatomical areas.

Measured: each section has one dominant all-cell component by radius 8*d0. S01 retains three isolated cells even at 32*d0, and its largest MST edge is about 670.25. No second large tissue piece is established at these scales. Small-radius fragmentation is scale dependent. A one-envelope rule can bridge empty regions and isolated cells; it must not be interpreted as anatomical continuity.

Measured: S02, S10 and S16 retain large bounded empty regions at both 8*d0 and 16*d0, robust to the finer raster checks. S02 is the strongest geometric cavity. Anatomy versus segmentation or acquisition gaps remains unresolved. No exact duplicate coordinates occurred; near-coincident cells are common in S05 and both S12 sections and S13. Do not remove or jitter those observations based on this audit.

Proposed support policy: all eligible cells define empirical tissue coverage; glial cells define projector rows. Preserve geometric gaps/components as metadata. Holdout expression masks do not cut geometry. Using known held-out locations is a fixed-design assumption, distinct from training-only response preprocessing.

Proposed topology policy: keep 19 registered sections independent, including the S12 pair. For a stationary ambient Mat?rn target, use a connected buffered computational domain containing all coordinates, initially the convex hull plus collar/buffer. Filling computational gaps is not an assertion of tissue there. Internal Neumann holes or independent subdomains encode different barrier/independence models and require a separate scientific choice.

Proposed common scale S=6532.12148032305, the median all-cell maximum span; per-section origin is its componentwise all-cell minimum. z=(x-origin)/S; inverse x=S*z+origin. Preserve original raw float64 coordinates. The inverse is exactly specified algebraically, not a guarantee of bitwise floating-point roundtripping. Derived maximum spans range 0.70437-1.16510. Historical glial-scale/common-scale ratios range 0.70386-1.15609. At fixed numerical inner h, ideal core vertex counts could scale by about 0.495-1.337 relative to historical normalization; buffers alter that estimate.

Mathematically derived: adopting the same numerical range prior after changing scale changes the native-coordinate prior. Old section-specific scales gave different native range medians. To reproduce those priors, ranges and direct-coordinate warp amplitudes (and paint-coordinate scales consistently) would need section-specific conversion. A shared native-unit prior is a proposed scientific amendment, not merely a serialization change. Physical cross-section calibration remains unresolved.

Proposed target: stationary continuum Mat?rn for the reference-coordinate warp field, nu=5, kappa=sqrt(40)/ell, covariance normalized analytically to unit variance before the recovered amplitude coupling sigma=ell*r/sqrt(10). The composed warped/paint response is not claimed stationary. The recovered direct-coordinate W model can use this approximation; no identity-plus-displacement replacement is needed. Natural finite-domain boundary effects are numerical error against this target, not the target itself.

Proposed contract: consistent P1 mass and ordinary gradient stiffness; natural outer weak form; full retained domain and generalized eigenspectrum; exact active marginal covariance without conditioning inactive values to zero. Active means nonzero projector column, independently of support/collar/buffer labels. Canonical zero-based vertices/triangles and observation rows carry IDs and hashes. CSR arrays have declared dtype, endianness, shapes, sorted indices and duplicate handling; authenticate logical arrays and file bytes. Store C,G1,A and full-mesh identities, spectrum provenance and hyperparameter-specific derived identities. Dense marginal covariance/root must be identified as dense. No lumping, spectral truncation, unreported jitter, variance renormalization or implicit coordinate changes.

Mechanical checks: positive triangles and mass SPD, stiffness PSD with appropriate null modes, eigen residual and C-orthogonality, valid projector barycentric weights and partition of unity, affine coordinate reconstruction, full-to-active agreement and positive-diagonal root convention. Scientific choices are the target law, support population, scale/prior, holes/barriers, shared flat/deep geometry and admissible accuracy; indexing/hash conventions and faithful algebra are mechanical invariants once those choices are adopted. A flat implementation is still unrecovered; shared geometry is a requirement for future comparisons, not an authenticated existing flat result.

## Proposed bounded numerical study

Complete machine-readable proposal: study_proposal.json. Resource planning only: resource_estimates.json. Neither file records mesh execution.

Select the predeclared six coverage sections using min-max-scaled geometry features and deterministic farthest-first coverage, forcing both S12 sections. Supplement before any covariance evaluation with maximum span S10, maximum MST edge S01 and minimum NN median S05. The nine are S01, S02, S04, S05, S07, S10, S12/Trem2_1, S12/Trem2_5xFAD2 and S13.

Derived central 99% prior interval: [0.275845417476973, 3.62521882417524]. Proposed inner h=ell_low/[2,4,8], fine collar ell_low/2, buffers ell_high and 2*ell_high beyond the collar. Two outward schedules are min(h+0.15*d,ell_high/4) and min(h+0.30*d,ell_high/2); d begins at the collar. Requested angle >=25 degrees and adjacent-edge ratio <=1.5 are proposed quality controls, to be measured rather than assumed.

Use 17 log-spaced central-interval ranges plus historical interior values .3,.6,1.65,2.72 and tail diagnostics .15,5 (23 total). Evaluate an independent analytic Mat?rn Bessel-K covariance at fixed physical-coordinate probes and compare against A U diag(1/q) U^T A^T. Never normalize each finite-domain covariance to hide variance error. Report both unit-base and amplitude-coupled errors.

Use 256 fixed observation probes stratified boundary/interior/dense/sparse, deterministic farthest-point selection and source-row ties; definitions and allocations in JSON. Include sparse extremes and persistent-void boundaries. Report distance bins, strata and per-section/range maxima. Validate all observation projector rows, not only probes.

Proposed primary thresholds: maximum unit-variance error <=.02, maximum absolute correlation error <=.02 and relative covariance Frobenius error <=.02 separately for every tested section/range; additional stratum reports may not be hidden by the aggregate. These are judgment-dependent trial tolerances intended to limit variance/prior distortion to a few percent, not previously established scientific tolerances. Secondary targets: correlation RMSE .005, 95th-percentile variance error .01. Report max absolute covariance error normalized by marginal scale where relative pairwise covariance is unstable.

Check full/active covariance agreement (proposed relative 2e-10), root reconstruction, conditioning, projector coverage, triangle quality, labels, h and buffer convergence separately. Check log-range and log-amplitude derivatives, including coupled sigma, with analytic continuum identities and finite differences at 1e-4/1e-5/1e-6; proposed nonzero relative derivative target 2e-5, plus scaled absolute errors near zero. Root derivatives require consistent positive-diagonal QR conventions. Synthetic directional algebra tests are permitted only in the future approved study, not MCMC.

Use Pareto tables across errors, total and active vertices, peak process-tree memory, eigensolve/QR/factorization/derivative times and projected sampler algebra cost. Eigensolve scales cubically with full vertices, storage quadratically; active-root cost also depends on active count. No runtime estimate is scientifically available before a pilot. Never select a candidate simply because it has approximately 175 active vertices.

Workload: 9 sections x 3 resolutions x 2 grading schedules x 2 buffers =108 geometries, each evaluated at 23 ranges =2,484 evaluations. Pilot the 12 S10 combinations first subject to resource checks; then complete the fixed experiment. Up to two finalists on the other ten sections add at most20 geometries/460 evaluations, for128/2,944 overall. Eigensystems are reused across ranges. No expansion if all fail without renewed approval.

Planning estimate, not a mesh result: triangular-lattice area integration predicts236-3,514 vertices; an illustrative threefold count allowance gives708-10,543. Sixteen dense float64 V-by-V work arrays could require up to1.47GiB ideally,13.25GiB under that count allowance, before other overhead. The factor three is a planning allowance, not a rigorous upper bound. Measured machine RAM about31.74GiB, available18.98GiB at audit; C: free654.47GiB. Propose concurrency1, total-process cap10GiB and8GiB available headroom; recheck before each candidate. Resource-excluded candidates are explicitly untested.

Accuracy scope: central99% is the proposed certification region; the finite experiment supports only empirical grid/probe claims. It cannot honestly establish a formal uniform error guarantee for all ranges and locations. That stronger claim requires suitable analytic bounds or interval certification. The unbounded1% prior tail remains unresolved for production: retain the prior, log tail coverage, and agree a stop/re-specify or independently validated fallback policy before MCMC. Do not silently truncate the prior, reject tail proposals or change meshes mid-chain.

## Decisions ready for review versus deferred

Proposed to freeze after approval: continuum reference-field target; all-cell support/glial observations; independent registered sections; raw-coordinate preservation and common-scale rule; explicit topology/model distinction; consistent FEM/full marginalization/shared-reference-geometry contract; fixed-design holdout geometry; bounded study protocol.

Unresolved until study or additional scientific decision: final h/grading/buffer, mesher/library and reproducibility controls, admissible error tolerances, verified interval/tail policy, physical units, anatomical hole classifications, acceptable sampler resource cost, any shared-prior amendment and near-coincident-cell provenance. No new legacy archaeology is proposed.

## Methodological sources

The SPDE/FEM relationship is described by Lindgren, Rue and Lindstrom (2011): https://rss.onlinelibrary.wiley.com/doi/abs/10.1111/j.1467-9868.2011.00777.x . Boundary-truncation analysis for specified SPDE windows and boundary conditions: https://arxiv.org/abs/1809.07570 . Neither source certifies this proposed adaptive geometry without the required numerical or analytic checks.

## Reproducibility and scope

Temporary reader.py authenticated allowlisted coordinate/identity datasets with the existing Anaconda Python and h5py, then transferred arrays in memory to Python3.12/SciPy for geometry only. The Anaconda SciPy spatial import failed before input reads; the workaround used existing interpreters without installing or modifying environments. Protocol, scripts, results, CSVs and contact-sheet plot are hashed in artifact_hashes.json. No expression arrays or candidate FEM matrices were read/generated. No repository or production artifact was modified.
