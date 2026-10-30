# SCTransform environment feasibility evidence

Observed: 2026-10-30, from clean baseline
`c88fdefd746887f0cca818b794ccfbce5035c9aa`. The user accepted this gate with the
[controlled environment amendment](../decisions/SCTRANSFORM_ENVIRONMENT.md).
Acceptance freezes a future build target; it does not certify an installed
environment or successful normalization.

The [small metadata record](evidence/sctransform-feasibility-20261030.json)
is a credential-free transcription of previously returned tool results, not a
verbatim terminal capture. It preserves measured observations and explicit
limitations. No authentication transcript or credential is included. No new
HPC connection or package acquisition was performed to write this checkpoint.

## Local measured environment

Discovery inspected PATH/application registrations, HKLM/HKCU R-core entries,
standard R installation/user-library locations and bounded executable patterns
under the two known Anaconda roots. It did not scan either disk recursively.
One R installation was found within these boundaries:

| Item | Observation |
| --- | --- |
| Executables | `C:\Program Files\R\R-4.4.1\bin\R.exe`, `Rscript.exe`, and their `bin\x64` counterparts; wrappers belong to one installation. |
| R/platform | 4.4.1, UCRT, x86_64-w64-mingw32; Windows 11 build 26300. |
| Library paths | `C:/Users/Data Viz/AppData/Local/R/win-library/4.4`; `C:/Program Files/R/R-4.4.1/library`. |
| Matrix | 1.7-0; DESCRIPTION says Repository CRAN, Built R 4.4.1, x86_64-w64-mingw32, 2024-06-14 08:26:22 UTC; no remote SHA field. |
| Other requested packages | Seurat, SeuratObject, sctransform, glmGamPoi, renv and BiocManager absent from these library paths. |
| Numerical libraries | `La_version()` = 3.12.0; sessionInfo BLAS/LAPACK path strings empty. Vendor/path not established. |
| Startup warnings | LC_COLLATE, LC_CTYPE, LC_MONETARY and LC_TIME could not use C.UTF-8. |
| Historical R path | `C:/Program Files/R/R-4.5.3/bin/Rscript.exe`, referenced by the historical launcher's configuration at review.py:22; absent locally. |

Queries used `Rscript.exe --vanilla -` with `R.version`, `.libPaths()`,
`sessionInfo()`, `extSoftVersion()`, `La_version()` and `read.dcf()` on the seven
requested package DESCRIPTION paths. No scientific package or historical
normalization script was run. Lack of a matching local install is not evidence
that the frozen versions cannot be built.

## Historical installation provenance and boundaries

Nonrecursive listings covered the known artifact root
`D:\johnston_brain\artifacts\GENE_REVIEW_20261004`, its `audit/` and `sections/`
directories, and the immediate `D:\johnston_brain` directory. Standard R roots
were also checked on C: and D:. Unrelated subprojects were not traversed.

Small records inspected: root `README.txt`, `BUNDLE_HASHES.json`, the launcher
Rscript-path configuration line, and `R_SESSION.txt`, `sct.log` and
`SCT_PROVENANCE.txt` in each of these ten section directories:

```text
S00__Trem2_5xFAD4  S02__Trem2_4  S03__Trem2_5xFAD3  S05__Trem2_3
S07__Trem2_5xFAD5  S09__Trem2_5  S10__WT5  S11__Trem2_5xFAD1
S12__Trem2_1      S13__Trem2_2
```

The prior committed B5 member-provenance inventory and B6 session capture were
also read; the archives were not re-extracted. No R package-source tarballs,
renv lockfile, container definition, installed-library DESCRIPTION provenance or
package-installation record was found within these inspected boundaries.
Project bundles were present; their presence does not identify package sources.

All ten 4,220-byte session files had SHA-256
`528c673bc16bf58b781747c03eb6b3554f62e9dfa25647ad23c3f677c4873cf3`.
They record R 4.5.3, Seurat 5.4.0, SeuratObject 5.4.0, sctransform 0.4.3,
Matrix 1.7-4, glmGamPoi 1.25.1 and LAPACK 3.12.1 on Windows. They also list
development dependencies, including DelayedArray 0.39.3, S4Vectors 0.51.3,
SparseArray 1.13.2 and BiocGenerics 0.59.7. Logs contain section-specific
START/COMPLETE markers, not package installation/source attestations. Identical
session files are not ten independent environment attestations.

## Official source checks

Only official repository metadata, commit-specific DESCRIPTION files and HTTP
HEAD responses were inspected. No package archive bodies were downloaded.
Direct CRAN requests initially failed in the browser tool; CRAN mirror listings
and subsequent direct HTTP HEAD queries supplied the observations below.

| Component | Exact source URL | HEAD result / bytes |
| --- | --- | --- |
| R 4.5.3 | https://cran.r-project.org/src/base/R-4/R-4.5.3.tar.gz | 200 / 40,518,619 |
| Seurat 5.4.0 | https://cran.r-project.org/src/contrib/Archive/Seurat/Seurat_5.4.0.tar.gz | 200 / 2,109,993 |
| SeuratObject 5.4.0 | https://cran.r-project.org/src/contrib/SeuratObject_5.4.0.tar.gz | 200 / 773,785 |
| sctransform 0.4.3 | https://cran.r-project.org/src/contrib/sctransform_0.4.3.tar.gz | 200 / 187,408 |
| Matrix 1.7-4 | https://cran.r-project.org/src/contrib/Archive/Matrix/Matrix_1.7-4.tar.gz | 200 / 2,485,182 |
| glmGamPoi 1.22.0 | https://bioconductor.org/packages/3.22/bioc/src/contrib/glmGamPoi_1.22.0.tar.gz | 403 from this client; official Git reference and DESCRIPTION accessible |

Bioconductor archive HEAD requests for 1.24.0 and 1.25.1, and package-index
requests for 3.22/3.24, likewise returned 403. This is an acquisition limitation,
not proof of missing source. A source URL is not a verified archive identity;
all archive SHA-256 values remain pending. The Windows R distribution and any
Windows package binaries require separate identity checks.

Official references resolved by `git ls-remote`:

| Repository / reference | Commit | DESCRIPTION SHA-256 |
| --- | --- | --- |
| satijalab/seurat v5.4.0 | `083a1b0d6c7732f2f116883885d79d6214ce180f` | `1004fa25ff83ce38534a991c6c72ae5236d8da03167525971238cb1219ee84ea` |
| satijalab/seurat-object v5.4.0 | `61b2d5c53ce7500c7df033b129f85f95749b8b42` | `bb306822ecb234413b1d6176f9abdf830bcd1277ba51a1ab234d96320738c4f9` |
| satijalab/sctransform v0.4.3 (peeled) | `49e35b5aeb76a602910207cbfde1561093340be3` | `5622d89dbb2c301865627c0fdc5f064be311252bbcc103868fc0e993c23570fb` |
| glmGamPoi RELEASE_3_22 | `908cde9d595259b4a317343ddfbcf20036ef0895` | `ae961003a5705acd92c522572fba81a2912ae5646f3f925a105e3473c04aee0e` |

The sctransform tag object is `8b9a9c9f395ce27f1d1222aed594794f91595c2a`;
the table records its peeled commit. DESCRIPTION hashes are hashes of the
small metadata files, not package-archive checksums. CRAN archives and Git
trees have not been compared for byte equality.

The official [CRAN package index](https://cran.r-project.org/src/contrib/PACKAGES.gz)
advertised MD5 `bd4458cced57f2ebe9f11a07d206821e` for SeuratObject 5.4.0 and
`205eb676c175048bed55b73f60f8def1` for sctransform 0.4.3. These are advertised
MD5 values, not independently measured SHA-256 values. Its renv 1.3.1 and
BiocManager 1.30.27 entries were observations, not frozen selections.

The author's repository HEAD and Bioconductor devel both resolved to
`95cffb79b02ce1239112d3c8b4adabfb448940bf`; its DESCRIPTION states 1.25.1
and hashes to `f2e562c186d4c56154989251c649b9d624e1efa082bf7d40a0445f7d7f16af40`.
The commit metadata dates it 2026-05-26. It predates the runs but has no recovered
run-to-source attestation. It is a retrievable historical-version candidate,
not the selected canonical version.
[Pinned metadata](https://raw.githubusercontent.com/const-ae/glmGamPoi/95cffb79b02ce1239112d3c8b4adabfb448940bf/DESCRIPTION).

The 1.22.0 release commit's
[DESCRIPTION](https://raw.githubusercontent.com/const-ae/glmGamPoi/908cde9d595259b4a317343ddfbcf20036ef0895/DESCRIPTION)
confirms the version selected by the user. The
[Bioconductor release table](https://bioconductor.org/about/release-announcements/)
pairs 3.22 with R 4.5; 3.23 with R 4.6. Source identification is distinct from a
tested installation of the complete dependency graph.

## HPC measured environment and uncertainty

Read-only SSH queries reached the approved login host on port 222. No jobs,
containers, builds or normalization were executed. Module loads affected only
the query process environment; no HPC files were edited.

| Item | Observation |
| --- | --- |
| Login node | CentOS Linux 7, x86-64, kernel 3.10.0-514.2.2.el7.x86_64 |
| R | R/gcc/4.4.0 points to /work/apps/R/4.4.0; executable reports R 4.4.0, x86_64-pc-linux-gnu |
| Module discrepancy | R module-whatis says 4.3.1; executable version is 4.4.0 |
| R module dependencies | pcre2/10.35, gcc/9.4.0, java/17.0.5 |
| Container modules | singularity/2.0 and singularity/2.3.1; no Apptainer in queried listings/PATH |
| Runtime | /cm/local/apps/singularity/current/bin/singularity reports 2.3.1-dist |
| Helpers | action-suid, create-suid, expand-suid, export-suid, import-suid, mount-suid are root-owned, mode -rwsr-xr-x |
| Configuration probe | /cm/local/apps/singularity/current/etc/singularity/singularity.conf not found |
| Namespace probes | No values returned for the queried proc paths; availability is unresolved, not established as disabled |

Installed setuid helpers suggest an intended user execution route (inference),
but do not establish site permission for our image. Compute-node differences
were not inspected. Modern container compatibility is **unverified**, not a
measured failed container run. Do not assume that a modern SIF image will run
under 2.3.1. See [Singularity 3 image formats](https://docs.sylabs.io/guides/3.0/user-guide/build_a_container.html)
and [Apptainer requirements](https://apptainer.org/docs/admin/latest/installation.html).

Remote command bodies actually used, with authentication material excluded:

```bash
uname -srm; cat /etc/os-release; type module
module -t avail R apptainer singularity 2>&1
command -v apptainer singularity
apptainer --version 2>/dev/null; singularity --version 2>/dev/null
module show R/gcc/4.4.0 2>&1
module show singularity/2.0 2>&1; module show singularity/2.3.1 2>&1
module load singularity/2.3.1
command -v singularity; singularity --version; singularity help 2>&1
cat /proc/sys/user/max_user_namespaces 2>/dev/null
cat /cm/local/apps/singularity/current/etc/singularity/singularity.conf
ls -l /cm/local/apps/singularity/current/libexec/singularity/bin/*suid*
cat /proc/sys/user/max_user_namespaces /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null
module load R/gcc/4.4.0; R --version
```

## Interpretation and accepted next boundary

Exact historical reconstruction is not certified. The user instead selected
R 4.5.3/Bioconductor 3.22 and released glmGamPoi 1.22.0 while retaining the four
recovered Seurat/Matrix package versions. Uniform regeneration and validation
are the objectives. The old HPC runtime is removed from the initial critical
path by selecting local Windows execution.

renv alone does not freeze OS/compiler/numerical-library behavior. The accepted
strategy combines a real renv lock, immutable source/binary identities and
local session/build records, then adds a Linux verification container after
the local environment works. [renv guidance](https://rstudio.github.io/renv/articles/docker.html).

Open build tasks: authenticated archive/binary acquisition and SHA-256 values,
Windows R/toolchain identities, complete dependency resolution, actual lockfile,
method/fitting-population assertions, deterministic synthetic validation, and
separately approved S00 smoke before the 19-section run. None was performed or
approved for execution by this documentation checkpoint.
