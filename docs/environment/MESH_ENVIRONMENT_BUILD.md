# Mesh environment build and bounded validation

Status: **accepted; materialization, minimal synthetic checks and fresh offline restoration pass**.
Repository baseline: `cfd00047d884021bed52194eb70189fd9cddc268`, main, initially
clean and equal to origin/main. The user authorized dependency acquisition and
installation in a new isolated external root, not Phase-0 implementation or S10.

The external machine-local root is
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\mesh-phase0-20261031`.
The environment is additive. No broader historical search, historical builder,
real response arrays, real meshes, S10, FEM accuracy study, MCMC or HPC was used.

## Runtime and package identities

Rscript was reused from
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031\R-4.5.3\bin\x64\Rscript.exe`.
The independent mesh library is `mesh-phase0-20261031\r-library`.
The whole reused R distribution (4,472 files) has unchanged tree digest
`b3cfc3b180947eee6cd6bf54ba594e75ecbad54aec73055a7ef0279f3c346437`
before installation and after validation. The tree encoding is sorted relative
path, tab, byte size, tab, SHA-256, LF for each file, then SHA-256 of the UTF-8
concatenation. Runtime executable hashes are in the
[runtime lock](../../environment/mesh/runtime-lock.json).

fmesher remains **0.7.0**, matching the recovered lineage version. Its
[official CRAN source archive](https://cran.r-project.org/src/contrib/Archive/fmesher/fmesher_0.7.0.tar.gz)
is 1,447,820 bytes, SHA-256
`6a1c4e69c5d2a235edcc3a613cb0cff0015ceee78b65c2d342bc05e12ff8a185`.
Its acquired DESCRIPTION declares R >= 4.1.0, C++17 and compilation required.
R 4.5.3 satisfies the declared R constraint; actual successful loading and tiny
mesh execution establish the tested runtime compatibility.

The matching [dated CRAN Windows binary](https://packagemanager.posit.co/cran/2026-03-12/bin/windows/contrib/4.5/fmesher_0.7.0.zip)
is 2,796,824 bytes, SHA-256
`47a4f6fb693a859b5245193be2113b2cd527c3f45e00cad6f0e1d834aed395a1`.
No compiler or system library installation was required. All 33 non-base R
packages have acquired source and binary archives, exact versions and hashes.
All 126 source/binary dependency constraints passed before installation.
The requested packages are fmesher 0.7.0, sf 1.1-0, Matrix 1.7-4 and jsonlite 2.0.0.
See the [complete version table](../../environment/mesh/RESOLVED_PACKAGES.md),
[acquisition lock](../../environment/mesh/r-source-lock.json), and
[complete R package record](../../environment/mesh/r-packages.lock.json).
Version agreement is not a claim that source-to-binary reproducible builds were
verified. No new fmesher version or SciPy mesher was substituted.

The new Python executable is `mesh-phase0-20261031\python\Scripts\python.exe`.
Its immutable base is the existing `C:\Program Files\Python312\python.exe`,
Python 3.12.0, x86_64. Base executable SHA-256:
`42ac541168e97dedb9aabd8be335539fc41c682e414b9e8d137b164fb68683b0`.
The base DLL and ensurepip identities are also recorded. Its installer was not
reacquired; this gate authenticates the local runtime, not a fresh Python build.
The venv resolves the full requested stack in one interpreter: NumPy 2.5.4,
SciPy 1.18.1, h5py 3.16.0, psutil 7.2.2 and jsonschema 4.26.0, plus their five
transitive wheels. pip 23.2.1 comes from the hashed Python ensurepip wheel.
Actual wheel compatibility resolution, offline hash-required installation,
`pip check`, distribution versions and paths all passed. The
[wheel lock](../../environment/mesh/python-source-lock.json) records exact
official PyPI artifact URLs and hashes, not the older M3 interpreter mixture.

## Isolation and numerical libraries

Both fresh R sessions used only the mesh library plus the immutable R base
library. Every loaded non-base namespace was asserted to resolve under the mesh
library. No user/site or SCT extension-package library fallback was used. Python
excludes system site-packages and checks every locked distribution's location.
The existing SCT package library, global/user libraries, raw data, production
bundles and historical artifacts were not modified.

R reports LAPACK 3.12.1 and default matrix products. sf reports GEOS 3.14.1,
GDAL 3.12.1 and PROJ 9.7.1, with s2 enabled. Python's h5py reports HDF5 2.0.0.
Wheel build records report NumPy OpenBLAS 0.3.34.106.0 (ILP64) and SciPy OpenBLAS
0.3.31.dev (LP64); exact wheel hashes pin these bundled libraries. The latter is
a bundled-library build label, not an independently installed Python package or
an assertion of identical NumPy/SciPy BLAS. Architecture/compiler/SIMD records
are preserved in the [numerical configuration](evidence/mesh-phase0-20261031/python-numerical-config.json).
Upstream wheel build-machine paths are metadata, not local dependencies.

## Measured bounded checks

The final [validation summary](evidence/mesh-phase0-20261031/validation-summary.json)
and [R session](evidence/mesh-phase0-20261031/R-fresh-1-session.txt) provide the
measured results. All synthetic outputs remain outside Git.

| Check | Measured result |
| --- | --- |
| Two independent fresh R sessions | Both pass, no recorded warnings |
| Tiny deterministic unit-square mesh | 13 vertices, 16 triangles |
| Vertex/edge/interior projector | 3 by 13, 6 nonzeros |
| Maximum projector row-sum error | 0 |
| Maximum affine coordinate error | 0 |
| R Matrix Market read/write error | 0 |
| R-to-Python sparse values/dimensions | Exact |
| Python-to-R sparse pointers/indices/values | Exact |
| Synthetic HDF5 roundtrip | Exact |
| Indexing corruption rejection | Both deliberate errors rejected in each session |
| Repeat semantic hashes | All four identical between sessions |
| Generalized eigenvalue maximum error | 1.7763568394002505e-15 |
| Generalized eigen residual maximum | 3.552713678800501e-15 |
| Mass-inner-product orthogonality error | 2.220446049250313e-16 |
| Half-order Bessel relative error against closed form | 2.220446049250313e-16 |
| Order-5 Bessel K at four positive arguments | Finite and positive |
| Process-tree RSS exercise | Live child detected; 3 processes, 94,371,840 bytes |
| Archive integrity | 66 R archives and 10 wheels match hashes |
| Canonical run manifest and section registry | Both authenticated; order agrees |

Wire triangles are explicitly converted once from R one-based to zero-based.
Matrix Market remains its standard one-based file representation; library
readers handle this and no additional subtraction occurs. Synthetic first and
second coordinate axes retain their order. This is compatible with future
center_y/center_x ordering; no real coordinate data or physical-unit claim is
tested here. Coordinates remain source_native under the scientific decision.

Repeat payload hashes:

| Payload | SHA-256 |
| --- | --- |
| Vertices | a64132f6df2c763f23c9342829038d67f0820855e1f779ec1fd7648293c42595 |
| Zero-based triangles | f16ab81c72a64d80472d418fe587136b2c190acbf2303b3fa8389b62765a8924 |
| Query points | 71ea2286a0f368fc3c644c5b52cf840e1b6a3a29c481a7c5bc82e51115c136e5 |
| Dense logical projector | 0c2c5005c001f032861838dedf404de0d416e434246ca66a9de867529244b6b3 |

## Diagnostics, limitations and review boundary

An initial Python report read used the Windows default text encoding and failed
on pip's UTF-8 metadata. It was corrected before Python installation. Initial
synthetic checks passed but emitted Matrix/SciPy sparse-conversion deprecation
notices and optional PyYAML-formatting notices. The final checks use explicit
CsparseMatrix/spmatrix conversions and dictionary numerical metadata, avoiding
those deprecated/default formatting paths without suppressing warnings or
installing an unnecessary dependency. One added namespace-audit attempt failed
because R disallows querying the base namespace that way; its path query was
corrected. Those diagnostic attempts remain external and are not counted as
successful final validation. A cached fmesher source URL attribution was also
corrected to the original official archive URL; its bytes/hash did not change.

The final fresh sessions have empty recorded warning lists; sf's linking banner
is informational. No stack-imbalance warning occurred. A stack-imbalance message
remains fatal in these checks. No historical environment equivalence is claimed
beyond retaining fmesher 0.7.0. Source compilation, Linux/container portability,
cross-platform determinism, future optional dependency needs and real study
accuracy/resources are untested. A second full installation from cached locked
archives now passes; see the [offline restoration receipt](MESH_ENVIRONMENT_RESTORATION.md).

The [build guide](../../environment/mesh/README.md) supplies exact interfaces and
restoration instructions. Commands and integrity identities are retained in
[installed-integrity.json](evidence/mesh-phase0-20261031/installed-integrity.json),
the installation record and validation summary. The full original pip resolver
report, package caches, installation logs and runtime file inventory remain in
the external root. This proposal contains only new environment tooling, locks,
small metadata and documentation. No Phase-0 harness has been implemented and
no study phase has run. The user authorized the focused environment commit after
the offline restoration and acceptance checks passed; no Phase-0 implementation
or S10 execution is authorized by this gate.

Repository text captures use UTF-8/LF; trailing presentation whitespace in R
session text was removed. These are normalized metadata copies, not claims of
byte-identical raw captures. The [capture index](evidence/mesh-phase0-20261031/capture-index.json)
records both the external originals and proposed repository file hashes/sizes.
Schema, version/lock consistency, source identities, local documentation links,
credential-pattern, syntax and diff checks pass. The restoration wrapper also
rejects the existing environment root before any acquisition or installation.
