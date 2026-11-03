# Layer-9 continuation review — proposal complete, not accepted

Accepted main: `eeb6d9a903663907bbcb2d081bcec05475788ee1`.
Preserved draft: `a87532ec30d6daacada3245e2cbeb105da4435ce`.
Final candidate worktree: `C:/Users/andyb/Desktop/bsfm-layer9-candidate`.
Earlier tested correction snapshot: `C:/Users/andyb/Desktop/bsfm-layer9-review`.
The second worktree allowed work on additive fixes without changing any file
under the running 195-test accepted-layer validation process.
All corrections remain unstaged. Main is unchanged. No scientific run or new
HPC job has been launched. This document is not a passing validation receipt.

## Authentication and restoration

All twelve entries in the draft's original inventory matched their recorded
byte sizes and SHA-256 before editing. That inventory describes the preserved
draft, not these subsequent corrections.

The HPC transfer receipt was independently hashed in the authenticated SSH
session and matched `5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60`.
No payload re-verification or scientific regeneration was repeated.

The selected historical driver was retrieved from its recorded HPC source path
into the external review environment directory. Its 94,890 bytes match SHA-256
`eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49`.
Only the existing bounded AST reference is evaluated; the historical driver is
not imported or executed as a program.

An isolated local Windows environment was restored from the unchanged Layer-5
wheel lock. Python is 3.12.0 and all three runtime binary hashes match the
accepted runtime identities. The runtime's actual base directory is explicitly
relocated; the old `C:/Program Files/Python312` path is provenance, not a required
installation location. No accepted environment, package version or source lock
was changed. External restoration scripts, installer signature/hash, package
receipt and test logs live under:

`C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/layer9-review-20261103`.

The environment authentication probe passed. The bounded historical
initialization comparison passed with exact state arrays, positions, warmup
keys and all four RNG stream identities. All 28 focused Layer-9 tests passed.
Independent authenticated historical warmup composition also matched state,
positions, histories, tuning and all four RNG endpoints exactly.

The unchanged committed same-environment Layers 1-3/provenance audit passed all
75 tests. Ordinary saved-fixture checks differ in low-order gradient bits on
this machine; their failures remain recorded, not waived or overwritten.
For Layers 5 and 6, independently evaluated original functions and port outputs match
exactly. For Layer 5 the only saved-fixture difference is one canonical-transition
leaf hash. Layer-6 saved differences include state/positions/fitted values and factor
outputs, while the same-runtime original chronology is exactly reproduced.
The hardware/compiler cause has not been established.

The ordinary accepted-layer suite ran 195 tests: 187 passed and eight failed
their saved-fixture gates (two Layer 3, three Layer 5, three Layer 6), with no
errors or skips. All source/test files remained unchanged during that suite.
These results do not constitute an ordinary 195-test pass. The separate
same-environment comparisons establish the narrower source/port claim.

## Conservative corrections under review

- Authenticate relocated runtime binaries by their unchanged accepted hashes.
- Cross-check every installed wheel's name/version/URL/hash against the accepted
  lock, rather than trusting a self-consistent installation receipt alone.
- Reject mutated in-memory run/input specifications before filesystem or RNG work.
- Bind the loaded genesis seed and warmup length to the immutable run specification.
- Validate initialization-to-warmup state/RNG continuity and genesis array shapes.
- Reject redirected writer-lock and segment-directory paths.
- Treat an unprepared truncated NPZ as preserved interrupted work that can be
  recomputed from the last committed boundary; a prepared corrupt pair fails.
- Independently read back completion after publication.
- Stage receipt JSON outside the transaction/genesis envelope, then publish
  only after flush/close. A killed partial receipt remains preserved without
  acquiring the authoritative prepared-receipt name.
- Add a saved-chart restoration boundary that validates the saved basis against
  authenticated FEM geometry using the existing spectral residual thresholds.
  It preserves the saved arrays, signs and ordering. Exact checkpoint comparisons
  remain unchanged. The canonical input loader uses this boundary on genesis resume.
  Final review added a strict nonnegative-modal guard, preserving the accepted
  constructor's clipping/domain invariant without clipping restored values.
- Copy each restored endpoint before a sweep advances its RNG objects. The first
  actual warmup/sweep exercise exposed aliasing of the in-memory genesis RNGs:
  after the first sweep, scanning the transaction chain saw an altered genesis
  predecessor and failed. The failed setup is retained in `layer9-focused-01`
  evidence; the corrected fresh-root run passed all 28 tests.
- Allow an explicit historical reference path while retaining exact source hash
  authentication; no old-drive dependency is used to infer source authority.

No accepted Layer 1–8 source, fixture, tolerance or scientific setting is changed.

## Review matrix and outstanding evidence

| Requirement | Current finding |
| --- | --- |
| Initialization chronology | Exact bounded historical comparison passed locally; one sigma2 draw and one initial PX, original literal sigma arithmetic |
| Sequential adaptation | Exact independent bounded historical composition passed; natural factor order, one eta draw after each endpoint, frozen tuning and unchanged master/global/gauge chronology |
| Genesis distinct from Layer 7 | Separate pre-sweep endpoint/envelope, not a fabricated sweep-zero checkpoint |
| Atomic sweep publication | Complete Layer-7 checkpoint and Layer-8 record paired and directory-published; named-boundary fault injection and fresh-process kill tests passed; interrupted receipt publication now tested and recoverable without sweep replay |
| Uncommitted recomputation | Prior RNG boundary restored; truncated-record and advanced-RNG discard regressions passed |
| Committed non-replay | Transaction head authoritative; fail-on-call projection repair and process-death tests passed |
| RNG resume | Actual synthetic two-arm continuation passed with four exact RNG endpoints |
| Target acceptance | Accepted Layer-5 constant remains 0.9; no 0.95 substitution |
| Runtime inputs | NPZ/JSON only; no runtime HDF5 bridge |
| Spectral chart | Additive restoration API integrated into candidate loader; full 36-test suite passed. Subsequent strict nonnegative-modal guard passed five focused chart tests plus retained-genesis exact restoration with eigensolve forbidden |
| Canonical input closure | Five synthetic runtime-reader checks passed: valid closure, changed payload, unregistered seed pair, broken certificate binding and reordered mesh rows. Real S10 loading/sampling is not claimed |
| Full test closure | Ordinary accepted suite 187/195 passed, eight saved-fixture failures; separate same-environment source/port checks passed; canonical October-26 suite ran 8 tests with 7 passing and 1 R-dependent skip |
| R mesh environment | Unavailable locally; Linux build's terminal timeout is preserved. Missing R-dependent tests must be reported as unavailable/skipped, never passed |

The expanded Layer-9 suite ran 36 tests with zero failures, errors or skips, and
unchanged source during execution. The final modal-domain guard was added after
that run; its five focused chart tests and retained-genesis integration check
passed separately. No claim is made that the final guard existed during the
earlier fresh 36-test run. Numerical initialization/adaptation/sweep kernels did
not change. The five runtime-input checks are additional synthetic reader tests.

The preparation artifacts are full-data mechanical inputs, not eligible primary
holdout-scoring inputs. The next scientific milestones remain separately gated:
Layer-9 review, then one specified S10 integration smoke, then the approved
training-only leave-out vertical slice. No large section/hole-size grid is started.
