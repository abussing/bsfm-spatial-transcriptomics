# Canonical four-stage warp mesh acceptance

Explicit user approval accepts the corrected October 26 four-stage builder as
the canonical practical mesh implementation. Baseline:
`4e362b6b3988e1b899d4250812ddfc4040beb819`. The canonical construction is a
parsimonious basis for latent warp inference. Outward grading and exact
inactive-vertex marginalization are load-bearing; historical vertex counts
are regression observations, not scientific optimization targets.

The successful S10 source files remain byte-identical to those recorded in the
[corrected reproduction](../october26_S10_localization_20261102/corrected-reproduction.json).
The four historical/corrected output pairs (vertices, triangles, projector and
mesh RDS) were rehashed and remain byte-identical. No real mesh was generated
again during acceptance. [acceptance.json](acceptance.json) records the checks.
The configuration changed only its approval-status string; its scientific
contents remain identical to the successful reproduction configuration.
The original report and its generating hashes are preserved unchanged.

The permanent regression now invokes the actual Python `build()` command path
with the configured JSON file. A test wrapper evaluates the actual R builder
prefix and stops before reading mesh inputs. It verifies that JSON integer 25
becomes R double 25 and that fmesher's native-facing requested angle is double
25 rather than falling through to its 21-degree default. A test-only copy with
the conversion removed fails. No real section or synthetic mesh is built by
this particular test; existing integration tests retain their synthetic coverage.

Validation at acceptance:

| Check | Result |
| --- | --- |
| Complete Python discovery, mesh/R integration enabled | 127 tests passed; zero failures, errors or skips; 82.702 seconds |
| Isolated R count-validation test | 7 cases passed, including invalid-input rejection |
| S10 source and four exact artifact pairs | Reauthenticated without regeneration |
| Config change | Approval-status metadata only |
| Documentation, JSON, syntax, hashes, credential patterns, whitespace | Passed before staging |
| Staged file/byte review | Small source/config/documentation/audit records only; no scientific arrays, environments or large logs |

The exact full-suite command, timing and external log identity are in
[python-tests.json](python-tests.json). R command/output and reproduction hashes
are in [acceptance.json](acceptance.json). The
[changed-file inventory](committed-files.txt) lists the exact intended commit
paths and is checked against the staging index before commit.

M3/Phase-0 range-derived geometry is rejected for production and retained only
as experimental evidence. Its launcher/configuration cleanup is deferred to the
next separately bounded task. No all-19-section mesh run, GP initialization,
Gibbs sampler, holdout work or HPC execution occurred. Only the accepted
canonicalization checkpoint is committed; it does not launch subsequent work.
