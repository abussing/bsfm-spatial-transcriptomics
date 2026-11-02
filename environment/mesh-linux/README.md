# Linux R mesh environment build

Status: source archives acquired and authenticated; builder syntax/CLI checked.
Job 22012386 passed configure but failed while generating optional NEWS.pdf,
before runtime/package installation. Its [receipt](../../docs/environment/HPC_R_MESH_BUILD_22012386.json)
and [package report](../../docs/environment/HPC_R_PACKAGE_VALIDATION_22012386.json)
remain failed. This does not replace the
accepted Windows lock or establish a Linux mesh result.

The proposed retry adds only `PDFLATEX=` to the make command. The authenticated
R source's `doc/Makefile` explicitly skips NEWS PDF generation when this variable
is empty. R sources, configure arguments, compiler settings, package pins,
installation order and validation are unchanged. This correction has not yet
been exercised by a new allocated build; it does not overwrite job 22012386.

`build.py` uses the existing R 4.5.3 runtime-source hash from
`../sctransform/source-lock.json` and all 33 package source hashes/versions from
`../mesh/r-source-lock.json`. It builds into a fresh external prefix with a
separate R package library. No dependency resolver or download runs during the
build. Source acquisition on HPC is recorded in
`/work/abussing/bsfm-consolidation/environments/r-linux-sources/acquisition.json`.
All 34 source archives passed the committed size and SHA-256 checks.

The existing conda compiler/sysroot, GDAL, GEOS, PROJ, OpenSSL, Abseil and UDUNITS
runtime remain read-only external dependencies. This is not a standalone
environment or a claim of byte-reproducible compilation. The receipt records
compiler hashes and conda metadata hashes. Full system-library authentication,
independent offline restoration and Python mesh-runtime restoration remain
separate work. This first job builds only the R side.

The existing conda prefix has UDUNITS 2.2.28 runtime libraries but lacks headers.
`udunits-headers.json` authenticates the matching conda-forge package and the
three C headers extracted from it. Only those headers are used; no foreign
executables or R packages are copied into the new environment. A linker symlink
inside the new output root points at the existing UDUNITS shared library.

The builder requires Slurm allocation, an explicit implementation commit and a
fresh output directory. It verifies all archives and headers before creating
the output. It builds R without bundled recommended packages, then installs the
locked package sources in dependency order, including the separately pinned
recommended packages. Each stage gets an external log; failure leaves its
receipt intact and prevents a passing status. A fresh R process must load all
33 exact package versions and check namespace-library isolation before success.
This is runtime validation, not mesh, SCT or sampler scientific validation.

Use the committed [bounded run specification](../../docs/environment/HPC_R_MESH_BUILD_RUN.json)
only after explicit HPC-job approval. Preserve failed output roots; retries need
a fresh destination and documented diagnosis.
