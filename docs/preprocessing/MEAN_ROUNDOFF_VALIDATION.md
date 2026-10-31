# Independent centering-mean roundoff check

Status: validator correction accepted by explicit user approval. The later
separately approved v2 production run passed for all 19 sections; see the
[production receipt](audits/20261031_production_v2/README.md).
Baseline: `3999bcc2f7cadb3e3ffdc77e510a69b70424a213`.

The first production run stopped during S01 payload validation because a generic
`atol=rtol=1e-14` comparison did not account for accumulation length and memory
layout. S01's fit and stored arithmetic means are valid; this was an over-strict
validator check, not a scientific fit failure. The v1 ledger remains **failed**,
with S00 promoted, S01 retained/unpromoted, and 17 sections unstarted. Every file
in v1 is retained byte-for-byte. No v1 artifact is repaired, promoted or reused.

## Numerical contract and derivation

NumPy documents that summation precision depends on the reduced memory axis;
partial pairwise reduction is not used identically for every layout. Thus two
correct binary64 reductions need not give identical means.
[NumPy 2.1 summation notes](https://numpy.org/doc/2.1/reference/generated/numpy.sum.html).

For binary64 round-to-nearest, let epsilon = 2^-52, u = epsilon/2 = 2^-53,
and gamma_k = k*u/(1-k*u). The standard forward-error estimate for summation
bounds the absolute error by gamma_(n-1) times the sum of absolute inputs.
[Higham (1993), section 2](https://nhigham.com/wp-content/uploads/2023/10/high93s.pdf).

The following is the project's derived comparison policy. Let

```text
m = (sum x_i)/n                      exact mean of the stored binary64 values
A = (sum |x_i|)/n                    exact mean absolute magnitude
mu_hat                              unchanged stored writer mean
r = math.fsum(x_i)/n                 independent reference, canonical cell order
A_hat = math.fsum(abs(x_i))/n
```

At most n-1 addition roundings plus the final division give the conservative
writer allowance `|mu_hat - m| <= gamma_n*A`; pairwise reductions fit inside this
sequential worst-case bound. By explicit conservative policy, the reference is
allocated the same gamma_n*A allowance as ordinary summation plus division.
This is not a claimed universal or sharp fsum error theorem. Python documents
fsum as high-accuracy with a rare double-rounding caveat; that documentation does
not prove the previously proposed gamma_3 bound. We retain fsum/n as a diagnostic
reference but do not rely on that gamma_3 claim for acceptance.
[Python 3.13 math.fsum](https://docs.python.org/3.13/library/math.html#math.fsum).

Using writer_allowance = gamma_n and conservative_reference_allowance = gamma_n,
the comparison policy and frozen safety factor S=2 are:

```text
A_upper = upward(A_hat / downward(1 - gamma_n))
B       = upward(2 * upward(upward(gamma_n + gamma_n) * A_upper))
pass    = abs(mu_hat - r) <= B        for every gene/type pair
```

Gamma calculations also round their denominator downward and quotient upward
using nextafter. The factor two covers floating evaluation of the discrepancy
and bound with conservative slack; it is not fitted to S01's observed error.
There is no unexplained absolute floor. An all-zero group has B=0 and requires
an exactly zero stored mean. The implementation rejects nonfinite/negative
responses, unsupported lengths, overflow and subnormal domains where this
relative-error model does not apply. Actual nonzero responses are log1p of
positive integer corrected counts, far from underflow. The group size must be
exactly representable and n*u<1.

The policy is frozen in `single-section-run.json` and checked against
`mean_roundoff.MEAN_POLICY`. The validator records all 91 x 3 reference means,
mean absolute magnitudes, discrepancies, bounds, individual pass flags, group
sizes, epsilon, unit roundoff, every discrepancy/bound ratio and their maximum. The reference
uses authenticated modeling-column order, with no sorting or population change.
Full repeated validation compares this report; fast resume authenticates its
file hash and policy/pass identity without recomputing numerical reductions.

## Retained-data audit

For Sox10/OGC in S01, n=4,720:

| Quantity | Value |
| --- | ---: |
| Stored writer mean; NumPy writer/F-layout mean | 1.4270851667900744 |
| Old validator sum/n | 1.4270851667900435 |
| NumPy one-dimensional mean; C-layout mean | 1.4270851667900435 |
| math.fsum/n; mean absolute magnitude | 1.4270851667900435 |
| Writer absolute difference from reference | 3.086420008457935e-14 |
| Writer relative difference from reference | 2.1627440886378557e-14 |
| Old combined allowance | 2.4270851667900437e-14 |
| New calculated allowance | 2.9913147457954244e-12 |

All 273 comparisons in each section were audited. Maximum absolute differences
below use math.fsum/n as the common reference; relative maxima and every pair
are in the [546-row table](audits/20261031_mean_roundoff/means.csv).

| Method | S00 maximum absolute difference | S01 maximum absolute difference |
| --- | ---: | ---: |
| Stored writer / writer-layout NumPy mean | 2.7977620220553945e-14 | 3.086420008457935e-14 |
| Validator scalar NumPy sum/n | 4.440892098500626e-16 | 8.881784197001252e-16 |
| One-dimensional NumPy mean | 4.440892098500626e-16 | 8.881784197001252e-16 |
| C-layout axis mean | 4.440892098500626e-16 | 8.881784197001252e-16 |
| F-layout axis mean | 2.7977620220553945e-14 | 3.086420008457935e-14 |

All 546 pairs pass their derived bounds. Largest discrepancy/bound ratios are
0.0138850 for S00 and 0.0152775 for S01. Maximum bounds are 5.99986e-12 and
6.64572e-12 respectively; adding 1e-10 to any of the 546 means fails. Exact `Y=L-stored_mean`,
arithmetic reconstruction, existing group-residual tolerances, all identities,
selection/order/membership and fresh saved-model count/log1p equality pass for
both payloads. S00's accepted logical hashes are unchanged.

The forensic audit first authenticated original execution/source/environment/
code identities under the clean baseline, then independently recorrected the
saved models into a separate evidence directory. The amended numerical check
was applied directly to the original read-only HDF5 payloads. This is explicitly
an audit across validator versions, not a production validation bypass: ordinary
production validation still requires exact code/configuration identities.

## Preserved scientific behavior and next gate

The writer, SCTransform, corrected counts, single log1p, panel, selected cells,
ordering, centering populations and stored means/Y are unchanged. Exact
`Y=L-mu`, reconstruction atol=1e-15/rtol=1e-14, group-residual atol=1e-12,
all hashes, provenance and source/environment checks remain enforced.

After this correction was committed and production separately approved,
S00, S01 and all remaining sections were recomputed from scratch in
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2`.
Do not resume, edit or merge the immutable failed v1 run. No production restart
is included in this correction gate.
