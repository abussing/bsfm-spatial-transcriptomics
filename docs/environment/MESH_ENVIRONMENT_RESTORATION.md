# Accepted offline mesh-environment restoration

Status: **pass; environment acceptance complete**. Repository baseline:
`cfd00047d884021bed52194eb70189fd9cddc268`. The user approved the initial build
subject to fresh offline restoration, matching bounded validation and
immutability checks before the focused environment commit.

Both machine-local roots are retained outside Git:

- Accepted environment:
  `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031`
- Fresh restoration check:
  `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-restore-check-20261031`
- External inventories and process logs:
  `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-restore-check-20261031-evidence`

No cleanup was performed. The accepted root remains authoritative for the
environment; the separate restoration root is retained as reproducibility
evidence. Neither is a real-section mesh output or Phase-0 result.

## Exact restoration and offline enforcement

Executed from the repository root:

```powershell
& 'C:\Program Files\Python312\python.exe' -B environment/mesh/restore.py `
  'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-restore-check-20261031' `
  --rscript 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031\R-4.5.3\bin\x64\Rscript.exe' `
  --python-base 'C:\Program Files\Python312\python.exe' `
  --offline
```

The destination was absent. The wrapper authenticated the shared R runtime,
Python executable/DLLs and ensurepip wheel, checked R package-lock and Python
requirements consistency, and authenticated all cached archives before creating
the root. Only the 66 recorded R source/binary archives and 10 recorded Python
wheels were copied. Neither installed R packages nor the accepted Python venv
were copied. The new venv was created from the authenticated base runtime and
its bundled ensurepip, then populated from the wheels.

`--offline` rejects any absent/mismatched cache rather than fetching it. The
R installer receives local ZIP filenames, explicit `lib=` and `repos=NULL`.
pip receives `--isolated --disable-pip-version-check install --no-index
--no-cache-dir --find-links <restored downloads/wheels> --require-hashes -r
<restored python-requirements.lock.txt>`. There was no network package
resolution, acquisition or version substitution. This is application-level
offline enforcement; no system network configuration was changed.

The [execution record](evidence/mesh-phase0-restore-check-20261031/execution.json)
contains every actual command, exit status, runtime and external log hash:
restore, fresh-process validation, archive/installation audit, semantic
comparison and immutability verification all exited zero. Restoration took
151.17 seconds; bounded validation took 10.67 seconds. The numerical test code
and its existing tolerances were unchanged. The
[restoration comparison rules](../../environment/mesh/restoration-spec.json)
were declared before restoration.

## Package and runtime equivalence

The [comparison record](evidence/mesh-phase0-restore-check-20261031/comparison.json)
contains the complete package manifest and archive identities. Results:

| Item | Original versus restored |
| --- | --- |
| R / Python | 4.5.3 / 3.12.0, equal |
| Non-base R packages | All 33 names and versions equal |
| R base packages | Complete recorded set equal |
| Python freeze | All 11 entries equal, including pip 23.2.1 |
| R source/binary identities | All 66 URL/size/SHA-256 records equal |
| Python wheel identities | All 10 URL/size/SHA-256 records equal |
| R library paths and loaded namespaces | Equal after replacing each mesh environment root; shared base-R path unchanged |
| Python isolation | Both exclude system site-packages; all locked distributions are local to their venv |
| R session, architecture, LAPACK, sf external libraries | Equal |
| NumPy/SciPy architecture and BLAS/LAPACK build configuration | Equal |
| HDF5 | 2.0.0, equal |
| Shared Python executable/DLL and ensurepip fingerprints | Equal before/after |

The restored environment uses fmesher 0.7.0, sf 1.1-0, Matrix 1.7-4 and
jsonlite 2.0.0. The [complete resolved version table](../../environment/mesh/RESOLVED_PACKAGES.md)
applies to both roots. Installed directories were not required to be byte
identical across roots: installation timestamps, venv paths and generated
path-specific metadata can differ. Archive identities and semantic runtime
configuration are the equivalence criteria.

## Repeated full bounded validation

Two fresh R sessions from the restored library both passed. The
[restored validation summary](evidence/mesh-phase0-restore-check-20261031/validation-summary.json)
and [session record](evidence/mesh-phase0-restore-check-20261031/R-fresh-1-session.txt)
show no recorded warnings. All four semantic hash pairs match exactly:

| Payload | Original and restored SHA-256 |
| --- | --- |
| Vertices | a64132f6df2c763f23c9342829038d67f0820855e1f779ec1fd7648293c42595 |
| Zero-based triangles | f16ab81c72a64d80472d418fe587136b2c190acbf2303b3fa8389b62765a8924 |
| Query points | 71ea2286a0f368fc3c644c5b52cf840e1b6a3a29c481a7c5bc82e51115c136e5 |
| Dense logical projector | 0c2c5005c001f032861838dedf404de0d416e434246ca66a9de867529244b6b3 |

| Check | Original and restored result |
| --- | --- |
| Tiny deterministic mesh | 13 vertices, 16 triangles |
| Projector dimensions / nonzeros | 3 by 13 / 6 |
| Maximum row-sum / affine reconstruction error | 0 / 0 |
| R-to-Python-to-R sparse roundtrip | Exact dimensions, pointers, indices and values |
| Synthetic HDF5 logical roundtrip | Exact |
| One-based/zero-based corruptions | Both rejected in each fresh session |
| Generalized eigenvalue error | 1.7763568394002505e-15 |
| Generalized eigen residual | 3.552713678800501e-15 |
| Mass-inner-product orthogonality error | 2.220446049250313e-16 |
| Half-order Bessel relative error | 2.220446049250313e-16 |
| All four order-5 Bessel values | Exactly equal, finite and positive |
| Canonical run-manifest and section-registry authentication | Equal and passing |

Process-tree detection passed in both environments: three processes including
the live child. RSS was 94,371,840 bytes originally and 94,392,320 bytes after
restoration. This expected process-memory difference is outside semantic
equality and is not a real-mesh peak-memory estimate. No tolerance was loosened.

## Immutability and verification limits

The [before/after receipt](evidence/mesh-phase0-restore-check-20261031/immutability.json)
records all roots and inventory digests. Full file-path/size/SHA-256 equality
passed for:

| Protected root | Files | Bytes | Result |
| --- | --- | --- | --- |
| Accepted mesh environment, including caches and records | 7,732 | 662,710,438 | Unchanged |
| Shared R 4.5.3 distribution | 4,472 | 199,241,259 | Unchanged |
| SCT extension-package library | 23,785 | 549,881,662 | Unchanged |

The shared R distribution also independently retains its existing locked tree
digest `b3cfc3b180947eee6cd6bf54ba594e75ecbad54aec73055a7ef0279f3c346437`.
The restoration inventory uses a different documented encoding (SHA-256 of
compact sorted-key JSON file records plus LF), so its aggregate digest differs
without a file-content difference.

For the unrelated global/user libraries, before/after path, byte-size,
mtime_ns and ctime_ns inventories passed for all 147,228 recorded files:
Anaconda site-packages, local R win-library, roaming Python packages, system
R 4.4.1 library and system Python 3.12 Lib. Documents/R remained absent. No
global/user package changes were detected; the installers' explicit paths,
fresh venv and R namespace checks establish their isolated destinations.

An initial attempt to hash every global-library file encountered a read-access
error in Anaconda. That optional broader content scan was abandoned before
restoration; no permissions were changed or bypassed. Global/user library
verification therefore uses metadata plus installation isolation, **not a
claim of complete content-hash verification**. Full byte authentication was
retained for all three protected project environment roots. The final policy
was declared before restoration. Incomplete preflight scans were not accepted
as evidence. No actual restoration/validation step failed or was retried.

Large before-state inventories, downloaded archives, installed packages,
synthetic arrays and logs remain external. The
[capture index](evidence/mesh-phase0-restore-check-20261031/capture-index.json)
records original and normalized metadata identities, plus external-only
inventory identities. Original build captures remain unchanged; the restored
installation audit records the final offline-enabled tool source hashes.

Windows-only validation remains an explicit limitation. No Linux/container
restoration, real-section mesh, S10, FEM accuracy/resource study, Phase-0 harness,
GP initialization or HPC work was performed. Environment acceptance does not
select a production mesh resolution or numerical design.
