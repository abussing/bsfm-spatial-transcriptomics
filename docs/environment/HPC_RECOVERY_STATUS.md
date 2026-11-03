# Existing HPC artifact recovery

Inspection date: 2026-11-02. This records read-only discovery and authenticated
file restoration, not a new model fit or mesh build.

## Original-desktop reconciliation

On 2026-11-02 the original Windows desktop independently rehashed the accepted
full-cell H5AD and canonical S10 export, authenticated all 28 F/code source-ledger
entries, and fast-validated all 19 canonical SCT-v2 six-file bundles from their
exact generating checkout. See the [desktop receipt](DESKTOP_RECONCILIATION_20261102.json).
No HPC/laptop transfer occurred. The bounded HPC absence findings below retain
their original machine/search scope; they do not imply global loss of these data.

## Recovered dependencies

All 19 historical section inputs exist and match the October-24 preparation
contract: [inventory](HPC_19SECTION_INPUT_INVENTORY.json). Their 300-gene raw
arrays cover 187,100 glial cells, with identities and coordinates. The production
scripts use these prepared inputs; their presence does not establish that the
original full-cell H5AD was transferred to HPC.

The historical `gene_review19_20261004_v1/review.py` preparation path reads
`E:/johnston_brain/Johnston_MERFISH_Data.h5ad`, fits/reuses section SCT on Windows,
then writes glial-only `input.npz` bundles. This agrees with the already committed
[recovery graph](../recovery/SCTRANSFORM_PREPROCESSING.md#raw-source-and-export-graph).
The inspected exporter was not executed. Alternative transfers remain possible.

The unextracted `SOURCE_INPUTS.zip` archive contains source-geometry members for
all 19 sections. Five S10 files were individually authenticated against the
committed mesh inventory, restored to a fresh external directory and rehashed:
`cells.csv`, `mesh_loc.csv`, `mesh_tv.csv`, `OBSERVATIONS_BASE.npz`, and
`INPUT_CONTRACT.json`. See the [restoration receipt](HPC_S10_GEOMETRY_RECOVERY.json).
This resolves the source-geometry export gap without generating an adapter or
executing historical code. Other sections' members were listed, not authenticated.

Two preview references, `mesh_loc.csv` and `mesh_tv.csv`, were subsequently
restored from exact duplicate prepared-mesh files. Both match the committed
preview hashes: [receipt](HPC_S10_PREVIEW_TOPOLOGY_RECOVERY.json). Only the full-cell
preview `A_proj.mtx` and `CERTIFICATE.json` remain unresolved among those four files.

## Search coverage and limits

The [search summary](HPC_RECOVERY_SEARCH.json) records four roots, depth six,
pruned environment directories, 15,869 visited directories, no unfinished
directories at that bound and no filesystem errors. It also records 13 archive
listings, including preparation, endpoint and snapshot transfers. The large
inventory stays outside Git with its path and SHA-256 recorded.

No H5AD/H5 or canonical `run-manifest` file was found within the filesystem search
scope. Relevant archive listings did not recover a full-cell raw input, canonical
response bundle or S10 preview reference. This is not an exhaustive absence
claim: other roots, greater depths, symlink destinations, renamed files and other
archives remain outside the inspection. Public downloading is not a prerequisite
for using the recovered historical data or continuing bounded sampler ports.

## Mesh runtime gap

The existing HPC conda R reports 4.5.2. Installed DESCRIPTION metadata reports
fmesher 0.7.0, Matrix 1.7-5 and sf 1.0-23. The accepted mesh environment instead
records R 4.5.3, fmesher 0.7.0, Matrix 1.7-4 and sf 1.1-0. Therefore the historical
environment cannot be labeled an exact restoration of the accepted environment.
Only the R version and package metadata were inspected; namespace loading and
canonical mesh execution have not been validated. Preserve that environment.

The exact R 4.5.3 source and all 33 mesh-package sources have now been acquired
and authenticated against the unchanged committed locks. The new
[Linux builder](../../environment/mesh-linux/README.md) is committed, staged on
HPC with matching hashes, and passes syntax, CLI and login-node refusal checks.
The [build specification](HPC_R_MESH_BUILD_RUN.json) requests four CPUs, 16 GiB
and two hours. The approved unchanged specification ran as job **22012386**:
configure passed, then make failed generating optional NEWS.pdf documentation.
Runtime installation, all package installs and fresh-session validation were not
reached. See the [execution receipt](HPC_R_MESH_BUILD_22012386.json) and
[package/version report](HPC_R_PACKAGE_VALIDATION_22012386.json).

The separately approved retry [22012400](HPC_R_MESH_BUILD_22012400.json) was
**TIMEOUT** at the terminal original-desktop check: exit `1:0`, elapsed
`02:00:09`, node432. The batch step reports `CANCELLED`, exit `0:15`, elapsed
`02:00:10`, MaxRSS `902232K`; the parent row has no MaxRSS value. R installation
and 20 packages completed, with lifecycle last. The build receipt remains
`started`; package-s2 has no recorded return code and its log ends at
`Using abseil-cpp from pkg-config`. No `validate.log` exists. The logs do not
establish why that stage failed to finish before the time limit.
The partial prefix and logs remain unchanged. No collector, retry, installation,
resume or duplicate submission occurred. Package/version/loading validation and
canonical Linux mesh reproduction remain unestablished; this does not undo the
accepted Windows environment or canonical mesh implementation.

## Remaining work

1. Plan transfer of the authenticated desktop full-cell input or canonical
   response bundles to the intended machine and verify destination hashes.
   Do not substitute glial-only counts for full-cell SCT fitting or historical
   expression for the accepted response. No further blind search is required.
2. Recover the two remaining S10 preview files or design an explicit reference-comparison
   route using the committed identities. Do not fabricate missing reference files.
3. Restore a separate Linux R mesh/SCT environment using the accepted package
   versions and new platform-specific provenance. A mesh rebuild needs its own
   committed run specification and explicit HPC-job approval.

The sampler CPU gate is already passed: [75-test audit](HPC_SAME_ENVIRONMENT_VALIDATION.md).
These remaining data/R dependencies do not undo it.
