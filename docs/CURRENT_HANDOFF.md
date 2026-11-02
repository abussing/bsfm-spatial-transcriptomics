# Current BSFM handoff

Verified baseline: `main`, `49f33c441e1cde9e1b8139ffef0103993eaa0222`
(Sampler Layer 3). Portability inspection: 2026-11-02.

Git is authoritative. Read [AGENTS.md](../AGENTS.md),
[CAPABILITIES.md](../CAPABILITIES.md), the
[sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md), and
[Layer 3](sampler/LAYER3.md) before implementation. Older checkpoint-specific
paragraphs describe their original scope; they do not undo later accepted layers.

## Completed and remaining work

- Canonical SCTransform v2 full-data responses passed for 19 sections at depth
  124. The final response is log1p(corrected counts), selected to the ordered
  91 genes and MIC/AST/OGC cells, centered once by section/type/gene.
- The October-26 adaptive mesh and GP-smooth SVD initializer are canonical,
  with bounded S10 reproduction evidence, not all-section production claims.
- Sampler Layers 1–3 implement Gaussian/shrinkage/PX updates, full-spectrum
  active marginalization, and the frozen L16/direct-W factor target.
- Layer 3 records 70 sampler and eight mesh tests passing on the former
  Windows machine. These are recorded results, not new HPC test results.
- A complete Gibbs sampler is not implemented. Fixed-physical-W hyper targets,
  joint-eta PCG, NUTS/adaptation, sweep chronology, checkpoint/restart,
  diagnostics, retained draws and launchers remain. Production GPU validation
  also remains. K, chains, run lengths and saving cadence are not selected.

Preserve the finite-feature likelihood (512 ordered nodes, 1,024 cosine-then-sine
features, ell_eta=.14), direct-W coordinates, all full-mesh modes and exact
inactive marginalization. Historical responses are not substitutes for canonical
SCTransform v2 responses. No settled scientific choice is reopened here.

## Available machines and artifacts

The former `C:\Users\Data Viz` machine and external E: drive are unavailable
to the current continuation. The old D:/E: paths are provenance, not retrieval
instructions for this machine. The local
`C:\Users\andyb\Desktop\johnston_brain\run_bundles` is a junction to E: and
does not supply another accessible copy.

HPC: `abussing@login.rci.sc.edu`, port 222; interactive authentication/Duo.
Never store authentication secrets in the repository. Read-only checks reached
`login001` and authenticated selected source and S10 reference files beneath:

```text
/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1
```

See [external-artifacts.json](external-artifacts.json) for known paths, hashes,
availability, classifications and recovery instructions. Hashes identify bytes;
directory names do not establish canonical status. The raw H5AD, newer canonical
response bundles and canonical `sampler-facing.npz` have not yet been located
on accessible storage. Searches were bounded, not an exhaustive absence proof.

**The historical 19-section HPC inputs are available.** All 19
`gene_review19_20261004_v1/sections/<section_id>/input.npz` files were authenticated
against the downstream production preparation contract on 2026-11-02. They retain
300-gene raw-count arrays, historical expression, coordinates and cell identities
for 187,100 glial cells. See the [per-file inventory](environment/HPC_19SECTION_INPUT_INVENTORY.json).
The October-24 production tree and subsequent adaptation/production directories
also exist. Their presence is not a new validation of historical model runs.
Do not describe this as missing all project data or requiring a public redownload.
The narrower unresolved dependency is full-cell preprocessing input: these
bundles contain glial subsets, while canonical SCT is fitted before that subset.
Continue tracing HPC preprocessing and transferred archives first.
The [recovery status](environment/HPC_RECOVERY_STATUS.md) records the expanded
filesystem/archive search, restored S10 source files and remaining R-runtime gap.

Public recovery now identifies the study's Brain Image Library dataset
[`ace-ear-nap`](https://api.brainimagelibrary.org/web/view?bildid=ace-ear-nap).
Its [2026-11-02 service update](https://www.brainimagelibrary.org/datacentermove.html)
reports continuing migration downtime; metadata works but data downloads timed
out. The archive's contents have not been matched to our required H5AD hash.
Recheck service status before retrying retrieval. Raw-data recovery does not
block bounded sampler ports using the authenticated historical source on HPC.

## Environment portability

The accepted [CPU lock](../environment/sampler-layer2/README.md) and builder
describe Windows CPython 3.12.0 and Windows wheels. They cannot be executed
unchanged on Linux. The existing HPC environment at
`/work/abussing/arka_trying_gpu_again/env` reports Python 3.11.14, JAX/JAXlib
0.7.0, NumPy 2.1.3, SciPy 1.14.1 and BlackJAX 1.3. It is historical evidence,
not a validated canonical environment, and must not be modified in place.

The login node has glibc 2.17. The official CPython-3.11 Linux wheel for pinned
ml_dtypes 0.6.0 requires glibc 2.27+. A separate CPU environment has been installed
under `/work/abussing/bsfm-consolidation/environments/sampler-cpu-py311` using
a successful source build of the same ml_dtypes version. The first approved
CPU test job ran all 70 tests but failed the gate: 58 methods passed, 12 failed
(17 failure records). That failure is retained. Follow-up job **22012334**
passed all **75 tests** and seven exact same-environment historical/port
comparisons, preserving the Windows fixtures and numerical tolerances.
See [HPC CPU setup](environment/HPC_CPU_SETUP.md), the
[initial result](environment/HPC_CPU_VALIDATION_22012327.json), and
[passing Linux audit](environment/HPC_SAME_ENVIRONMENT_VALIDATION.md).
Installed GPU package metadata is not GPU execution evidence.

## Resume sequence

1. Clone GitHub; verify origin, branch, HEAD and working-tree status. Read the
   documents above and the artifact manifest. Do not rerun completed recovery.
2. Authenticate accessible external files against the recorded SHA-256 values.
   Ordinary sampler fixtures and the frozen rule are already in Git and do not
   require the raw H5AD or historical drive.
3. Preserve the installed Linux environment and both CPU validation receipts.
   Same-environment source/port checks now pass; do not repeat that recovery.
   Full source-build reproducibility remains unestablished. Prepare a committed
   specification before further HPC jobs; follow AGENTS.md approval requirements.
   Do not run the scientific suite on a login node.
4. Trace existing HPC runs and transferred data for the full-cell input or
   canonical responses; the authenticated 19-section inputs above are the starting
   point. Public upstream retrieval is a fallback, not an established requirement.
   Regenerate canonical responses using the documented runner only after
   the accepted R environment is restored/ported and checked. A different raw
   payload requires explicit provenance reconciliation, not a renamed file.
5. Five exact S10 source-geometry files, including cells.csv, were restored from
   the HPC SOURCE_INPUTS.zip archive and authenticated against the committed
   inventory. See the [recovery receipt](environment/HPC_S10_GEOMETRY_RECOVERY.json).
   No geometry adapter is needed for these inputs. The two preview topology files
   were also recovered as exact duplicates; the preview projector and certificate
   remain unresolved. The Linux R build is prepared with authenticated sources
   and a committed specification, awaiting explicit job approval. Restore/validate
   the Linux mesh environment before a canonical rebuild.
   Existing historical mesh
   files are evidence and must not silently be relabeled canonical exports.
6. Continue the remaining sampler components as bounded ports with source maps
   and independent mechanical checks. This portability step adds no sampler
   functionality and does not select a scientific run configuration.

New Linux execution produces new provenance and may differ in serialized bytes.
Do not rewrite old receipts to claim reproduction. Keep large artifacts outside
Git, with stable HPC paths and completion manifests linking them to their exact
generating code/configuration/environment.
