# Roundoff audit evidence

Status: validator correction accepted by explicit user approval. See the
[numerical derivation and findings](../../MEAN_ROUNDOFF_VALIDATION.md).

[means.csv](means.csv) records all 546 gene/type comparisons, absolute/relative
differences, group sizes, magnitudes and calculated bounds. These are aggregate
means, not cell-level expression. [summary.csv](summary.csv) contains method
maxima; [review.json](review.json) records provenance and external evidence hashes.

V1 remains failed and byte-for-byte unchanged. Its failed S01 attempt is not
promoted or reused. S00 and S01 will be recomputed under a new committed v2
identity after separate production-run approval. No production has restarted.

Validation: 81 Python tests, seven R count cases, four synthetic fits and fresh
saved-model readbacks for S00/S01 passed. All five synthetic semantic hashes
remain unchanged per fit. No real section was refitted. The writer, R sources
and scientific panel/bundle contracts are byte-identical to baseline.

Amended policy: both writer and diagnostic reference receive gamma_n allowances,
with upward-rounded `B = 2 * (gamma_n + gamma_n) * A_upper`. This does not claim
a proven gamma_3 error bound for `math.fsum`. All 546 comparisons pass; all 546
positive 1e-10 alterations fail. Per-pair ratios and amended bounds are retained.
