# Sequential SCTransform production orchestration

Status: **implemented and production-validated for canonical full-data preprocessing**.
The explicitly approved v2 run recomputed all 19 sections from raw counts at
commit `6eb672bebbaf5cde6c9d50391aac275a210832a6`; all deep and closure checks passed.
See the [production receipt](audits/20261031_production_v2/README.md).
Full-data bundles are ineligible for primary holdout scoring; future primary
holdout experiments require training-only preprocessing.

The first run, v1, stopped on an over-strict S01 mean check and remains failed
and immutable. The accepted [numerical correction](MEAN_ROUNDOFF_VALIDATION.md)
was committed before the fresh v2 run. No v1 artifacts were reused. Earlier
uncommitted S00 review bundles remain review evidence, not production artifacts.

The launcher calls `response_run.run`; the single-section fitting core, response
construction, ordering, panel, depth 124, centering and deep numerical validation
are unchanged. Concurrency is fixed at one in
[production-run.json](../../config/preprocessing/production-run.json).
The [readiness snapshot](audits/20261031_readiness/README.md) supports input
eligibility and planning only, not successful fitting.

## Run layout and identities

```text
RUN_ROOT/
  run-specification.json    immutable identities and frozen order of 19 sections
  run-ledger.json           durable mutable checkpoints and session history
  run-manifest.json         complete/pass, created only at successful closure
  run.lock                 OS process lock, never evidence of completion
  sections/<section-id>/   exactly the six canonical bundle files
  attempts/.attempt-<section>-<uuid>/  temporary intermediates and failure evidence
  receipts/                optional single-section promotion receipts
```

Both standalone and orchestrated production require an actual committed HEAD,
a clean Git working tree (including untracked files), and source bytes matching
that commit. Every section records the exact commit and preprocessing source
hashes. The run specification also pins single-section configuration, production
policy, schemas, panel, registry, raw source, source stat identity and environment
locks. The launcher binds each execution.json to the run specification SHA-256.
Dirty scientific or documentation changes during a run stop further promotion.
The isolated environment's locks are authenticated; actual runtime package and
method checks continue in the existing R runner. This does not rebuild or
rehash every installed package during resume.

The existing parent directory is allowed; final sections are never overwritten.
Standalone invocation uses the same sections/attempts/receipts layout and an OS
lock, but refuses a root already owned by an all-section run specification.
Attempts and final sections must share a filesystem. Symlink/junction directory
paths are rejected. The OS lock is released automatically on process exit;
the small lock file can persist and is not a stale-lock failure flag.

## Authentication and resume

At each launcher start/restart, one whole-file SHA-256 authenticates the raw
source. An in-memory attestation can be consumed only in that process while
its source session remains active. It cannot be loaded from a ledger, JSON,
CLI argument or prior process. Path, size, mtime, ctime, device and inode must
remain unchanged. Each section still reads/checks the accepted cell/gene axes,
section selector, selected counts and required metadata. Deep pre-promotion
validation repeats the section checks with the same live attestation.
Standalone use still hashes the whole source itself.

After all 19 sections validate, closure rehashes the entire raw source. A hash
or stat mismatch prevents completion. Stat checks are a change detector between
the two full hashes, not a cryptographic substitute for final authentication.
The source must remain read-only operationally for the duration of a run.

Resume authenticates the complete run specification, current code, environment,
configurations and raw source anew. It does not trust directory existence or a
ledger's completion flag. A finalized section must pass the independent fast
closed-file check: frozen manifest schema, exactly six files, every file size
and SHA-256, original deep-validation pass/metrics, embedded logs and warnings,
run/section/code/config/source/environment identity and readback signatures.
The fast check does not refit, run R recorrection, or recompute numerical
HDF5 invariants; it verifies bytes and evidence from the original deep validation.
Ledger checks explicitly distinguish these two kinds of evidence.

A failed/incomplete section receives a new attempt. Failed attempts are never
deleted automatically. Corrupt or incompatible finalized bundles cause a stop;
they are not overwritten or silently recomputed. A crash after promotion but
before checkpoint can be recovered from the valid self-contained bundle.
A missing formerly promoted bundle is an error. Run roots/identities are never
merged, and a completed run manifest is not rewritten on a later integrity check.

## Checkpoints, cleanup and completion

Before fitting each section, record available RAM and free destination space.
Require at least 7 GiB available RAM and 10 GiB free disk; stop on failure.
Readiness estimates (56 minutes, 1.34 GiB final data) are extrapolations, not
guarantees. No parallel implementation is included.

Ledger updates write a same-directory temporary JSON, flush and fsync it, rename
atomically, and fsync the resulting file before proceeding. POSIX also fsyncs
the parent directory. Windows retries only transient sharing/access failures
of the atomic replacement (bounded backoff), preserving the prior checkpoint.
This provides recoverable checkpoint ordering; it does not promise protection
against every storage-device/controller power-loss failure.

Cleanup occurs only after promotion, fast bundle validation and a durable
promoted checkpoint. The ledger records cleanup intent before deletion and
completion afterward. The resolved attempt must be a direct child beneath this
run's attempts/ directory, match the authenticated execution attempt ID, contain
no failure marker and no linked descendants. The final sections directory is
never a deletion target. If cleanup was interrupted, resume can record an already
absent successful attempt. Failed attempts are retained, including an attempt
recorded as failed after a post-promotion interruption.

The six-file bundle has no authoritative dependency on attempts or receipts.
Raw source, exact code/configuration and isolated environment remain required
for an independent deep validation. Cleanup does not alter those requirements.

Completion requires the exact ordered registry inventory of 19 valid bundles,
start/final raw authentication, unchanged code/configuration/environment identities,
and an atomically written final run manifest. It contains each section manifest's
relative path, size and SHA-256, all source/config identities, timings, resource
observations, sessions and cleanup states. Schema definitions are
[specification](../../schemas/preprocessing/production-specification.schema.json),
[ledger](../../schemas/preprocessing/production-ledger.schema.json), and
[final manifest](../../schemas/preprocessing/production-manifest.schema.json).
Schemas supplement executable identity/state checks; schemas alone do not certify
that scientific code ran or that a matrix is valid.

## Recorded v2 production command

The user explicitly approved this exact command at generating commit
`6eb672bebbaf5cde6c9d50391aac275a210832a6`. The fresh destination was absent before
launch and now holds completed artifacts. This is an execution record, not a
new run authorization or an instruction to overwrite the completed root.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
& 'C:\Users\Data Viz\anaconda3\python.exe' -B -m bsfm.preprocessing.production_run `
  --raw-source 'D:\johnston_brain\Johnston_MERFISH_Data.h5ad' `
  --environment 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031' `
  --config 'config/preprocessing/single-section-run.json' `
  --production-config 'config/preprocessing/production-run.json' `
  --run-root 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_PRODUCTION\sctransform_full_data_v2'
```

Any later integrity validation or approved resume must use the exact generating
checkout; a later documentation commit is not an interchangeable run identity.
Never point this command at the immutable failed v1 root. Paths remain CLI
arguments, not scientific code constants.

Tests use temporary Git repositories, raw byte fixtures, simulated section
execution for state transitions, and separate synthetic six-file bundles for
the real fast validator. They do not pretend that mocked section completion is
scientific execution evidence. Existing Python corruption tests, R count tests
and fresh synthetic semantic-repeat tests remain required. Those implementation
tests did not constitute real-section production. The
separately approved v2 execution is documented above. No holdout preprocessing,
mesh, GP or HPC work is included. Coordinates remain source_native and full-data
bundles remain
ineligible for primary holdout scoring.
