# Unstaged Layer-9 review proposal

This candidate is **not accepted, committed, merged, or approved for scientific
data**. Main remains at `eeb6d9a903663907bbcb2d081bcec05475788ee1`.

Read [the implementation review](IMPLEMENTATION_REVIEW.md),
[validation receipt](VALIDATION.json), and
[next-run readiness](NEXT_RUN_READINESS.md). The latter identifies the work
between this local mechanical review and the requested overnight leave-out run.

## Review material

- `IMPLEMENTATION.patch`: all proposed runtime/test files against accepted main.
- `CORRECTIONS_FROM_WIP.patch`: changes relative to preserved WIP `a87532e`.
- `COMPLETE_PROPOSAL.patch`: implementation plus review documentation/receipts.
  It excludes generated patch copies and `INVENTORY.csv` to avoid circular hashes.
- `INVENTORY.csv`: exact byte sizes/SHA-256 for implementation and all review
  files, including the patches; excludes only itself.
- `SOURCE_MAP.csv`: scientific/source lineage and the new orchestration/API work.
- `SYNTHETIC_INVENTORY.json`: external retained synthetic execution artifacts.
- Original failed setup, saved-fixture failures, successful focused tests and
  separate same-environment comparisons are preserved as distinct receipts.

These patches do not revert the current handoff to the older WIP's handoff.
Original WIP capture/inventory remains preserved by its Git commit. Large logs,
environments, source captures and synthetic payloads remain outside Git.

## Environment proposal

`LINUX_ENVIRONMENT_PROPOSAL.json` resolves Linux wheels at the existing thirteen
locked package versions. `LINUX_BUILD_RUN_PROPOSAL.json` and
`build_linux_environment.py` describe a bounded isolated environment build.
Only release metadata resolution and Python syntax checking have run. No Linux
environment installation, numerical validation or scheduler submission is claimed.

## Local evidence commands

The external runner, restoration tools and retained logs are under
`C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/layer9-review-20261103`.
The isolated Python is `sampler/python/Scripts/python.exe` beneath that root.
CPU/x64 and one-thread BLAS settings were explicit. The fresh candidate suite
used `run_candidate_tests.py test_sampler_layer9*.py layer9-focused-03`.
The accepted-layer suite ran in the separate unchanged `bsfm-layer9-review`
worktree; the validation receipt checks accepted source/tests/config/environments
byte-for-byte against main in this candidate as well.

The ordinary saved-fixture suite and separate historical-reference audit answer
different questions. Neither is relabeled as the other. Synthetic warmup
divergences are retained in diagnostics; passing mechanical continuation does
not claim convergence or scientific adequacy.
