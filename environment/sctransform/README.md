# Materializing the local validation environment

The frozen version target is [environment-spec.json](environment-spec.json).
It records the pre-acquisition decision, not the current installed state.
The scientific and environment decisions remain separate from build evidence.

Use an external, user-owned directory. The initial build uses the official
[R 4.5.3 Windows installer](https://cran.r-project.org/bin/windows/base/old/4.5.3/)
with `/CURRENTUSER /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /TASKS= /NOICONS`
and explicit `/DIR=` and `/LOG=` arguments. Verify its published MD5 and record
SHA-256 and Authenticode status before execution. Do not alter system R or PATH.

`acquire_packages.py EXTERNAL_ROOT` acquires Windows binaries and matching
source archives. It resolves Depends, Imports and LinkingTo from captured
indexes, pins all frozen package versions, and records each archive hash. The
base/recommended library comes from R 4.5.3, including Matrix 1.7-4. The Seurat
5.4.0 binary is obtained from the dated 2026-03-12 Posit CRAN snapshot, because
the current CRAN binary index supplies a newer version. Bioconductor binaries
come from the official [Posit mirror](https://bioconductor.org/about/mirrors/)
for release 3.22. No version is substituted silently.

The resulting external `source-lock.json` is the acquired manifest. Matched
source/binary names and versions do not prove reproducible-build byte equality.
The R source archive contains the recommended-package sources; their member
hashes are retained separately. Keep all archives and libraries outside Git.

Run `install_locked.R EXTERNAL_ROOT` with the isolated R's absolute
`bin/x64/Rscript.exe --vanilla` path. It installs the acquired binary files
without resolving/downloading additional packages, verifies the frozen
versions, loads the namespaces, and generates an actual `renv.lock` from both
the external library and R's bundled library. It preserves installed-package
and session records. The lockfile complements the archive/source lock; a
moving CRAN URL alone is not the source identity.

After an interrupted install, `audit_installed.py EXTERNAL_ROOT --output-prefix
AUDIT_NAME` rehashes the source/binary archives and checks installed files
against each authenticated binary's MD5 inventory. Optional `--repair` restores
only exact binary-archive members using atomic per-file writes, then repeats
the check. It does not resolve new versions or execute package code. The
resulting verified-package `.txt` list can be passed as the second argument to
`install_locked.R` to avoid its slow serial checksum scan. Never reuse that
list after another interruption or package change; perform a new audit.

The 2026-10-31 build was interrupted by machine shutdowns. Incomplete files
and zero-filled in-progress source files were detected and repaired. Interrupted
logs remain external failure evidence, not successful installation certificates.
Only the post-repair audits and completed validation results support acceptance.

For bounded validation see the [runner guide](../../docs/preprocessing/SCTRANSFORM_VALIDATION.md)
and [run specification](validation-spec.json). No HPC job or other section run
is part of this build procedure.

For later reproduction, use `acquire_packages.py EXTERNAL_ROOT --lock
environment/sctransform/source-lock.json` rather than resolving today's index.
It verifies/restores that exact recorded archive set and fails on a missing
source or hash mismatch. Add `--verify-only` to check an existing cache without
downloads or rewriting its acquisition manifest. If an old binary URL expires,
use the retained external archive; do not substitute a newer binary. The R
Windows installer is separately identified in the lock and installed as above.
