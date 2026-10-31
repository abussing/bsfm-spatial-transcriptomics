# Local SCTransform environment build and validation

Date: 2026-10-31. Baseline: `f7d40588840887953b2cda2c562e58a21a9fa1dd`.
Status: **materialized; synthetic and bounded S00 checks accepted**.
No frozen scientific or package version was changed. This remains the deliberate
glmGamPoi 1.22.0 amendment, not historical byte reproduction.

The external environment is:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sctransform-20261031`.
It contains user-owned R 4.5.3, its bundled library, a separate `library/`,
downloads, installation records and the original acquired source manifest.
System R and its libraries were not modified; no administrator installation or
system PATH change was used. The actual validation interpreter is
`R-4.5.3\bin\x64\Rscript.exe` beneath this root.

## Authenticated material and lock coverage

- The 90,616,928-byte official Windows R installer has SHA-256
  `768ae31bb0b6056def5b1a9789a7dc49306bd037d69b0a99cdd90183aa0c1a31`.
  Its published MD5 matched `7750801cb615cb463a8c027cf8fbf1dd` and Windows
  Authenticode reported Valid, signer Martyn Plummer. URLs and hashes are in
  the [source lock](../../environment/sctransform/source-lock.json).
- Acquired 160 nonbundled packages as exact Windows binary archives and matching
  source archives. R's source archive supplies the recommended-package sources,
  including Matrix 1.7-4; member sizes/hashes are recorded. Package plus R-source
  archive bytes total 459,175,543, excluding the Windows installer and indexes.
- [renv.lock](../../environment/sctransform/renv.lock) records R 4.5.3,
  Bioconductor 3.22 and 175 packages, including recommended packages. All seven
  frozen version values agree with the environment decision. Build tools renv
  1.3.1 and BiocManager 1.30.27 are now recorded in the resolved lock.
- The source lock separately identifies binary archives, source archives,
  DESCRIPTION hashes, official Git metadata and the R distribution. Same
  package/version does not establish source-to-binary reproducible-build equality.
- The current CRAN binary index had newer Seurat and Matrix. Seurat 5.4.0 came
  from the 2026-03-12 Posit CRAN snapshot; Matrix 1.7-4 was bundled with R 4.5.3.
  Bioconductor 3.22 binaries came from its official Posit mirror. No compiler
  installation was needed because matching binaries were available.

Exact build/validation commands are recorded in
[execution-record.json](../preprocessing/audits/20261031_sct_smoke/execution-record.json).
The [build guide](../../environment/sctransform/README.md) explains acquisition,
locked restoration, isolated installation and integrity checking. Archive URLs
can expire; the retained external archives and measured hashes are part of
reproduction, rather than permission to substitute a newer dependency.

## Shutdown recovery and measured validation

User-reported machine shutdowns interrupted work. The latest shutdown left
27 package installations damaged and three in-progress repository files
zero-filled (`pyproject.toml`, the installer R script and the validation R
script). These were identified and restored; interrupted logs were not accepted
as successful completion records. The R distribution was repaired using the
same authenticated installer.

Repository copies of text metadata and `renv.lock` use LF line endings; session
copies also omit trailing display padding. Original
external records retain their acquired bytes; their original SHA-256 values and
the repository lock hashes are recorded separately. Line-ending normalization
does not change the JSON dependency graph or session contents.

The [post-repair package audit](../preprocessing/audits/20261031_sct_smoke/installed-package-audit.json)
rehashes every acquired package source and binary archive. All 160 packages
passed checks of 23,571 unpacked files after repair. Initial archive records and
the installer were also rehashed. Producer source hashes and every reported
SCT output hash were checked again after execution. Saved S00 objects were
reloaded and verified, including recorrection from the saved fitted model.

The bounded [validation report](../preprocessing/audits/20261031_sct_smoke/summary.md)
records four synthetic fits and one full S00 fit, followed by two S00 subset
repeatability fits. All passed the effective-method, actual fitting-population,
determinism, common-depth and exact layer-equality checks. S00 used all 20,719
eligible cells, 300 genes and depth 124. No other tissue section was normalized.

## Limitations and review boundary

A mixed-order namespace-loading diagnostic emitted `stack imbalance` warnings
after loading glmGamPoi. Sixteen individual dependency/namespace loads in fresh
R processes were clean, as were all seven actual validation fits and the saved
artifact readback. The warning's cause is unresolved; neither a dependency
version change nor warning suppression was used. The runner rejects that
warning if it appears in a fitting log. Preserve this finding for review before
generalizing beyond the tested execution path.

Runtime was Windows 11 build 26300, UCRT x86-64, LAPACK 3.12.1, locale C,
single-thread settings and sequential future execution. Cross-platform numerical
agreement, a Linux container, HPC execution, training-only holdouts and all-19
regeneration remain untested. Installed environments, archived packages, input
identifiers, expressions, models and large logs remain outside Git. This bounded build, implementation and validation evidence are accepted by
explicit user approval; no remaining section run is authorized.
