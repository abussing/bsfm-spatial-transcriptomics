# SCTransform evidence ledger through Stage B2

Checkpoint date: 2026-10-30. Scope: B1 metadata/provenance and B2 six-file source
inspection. Later B3 findings are deliberately excluded. No implementation has
been selected. Historical labels such as CURRENT and PRODUCTION confer no
authority.

## Evidence classes

| Class | Meaning in this ledger |
| --- | --- |
| User decision | Explicit instruction from the recovery conversation. |
| Documentation claim | Statement in a historical note, comment, contract or manifest; not automatically verified behavior or execution. |
| Implemented behavior | Static observation from identified source bytes; does not establish that they ran. |
| Execution evidence | Historical command/result/test record, with its specific limitations; no historical program was executed during B1/B2. |
| Downstream consumption | An explicit reader, path or source/output relationship; distinguish implemented/configured consumption from demonstrated run consumption. |
| Unresolved gap | Missing evidence, inconsistent claims, or an unverified relationship. |

Mathematical deductions are marked as deductions from implemented behavior, not
as empirical or execution evidence. File existence/size and measured SHA-256 are
mechanical observations, not scientific validation.

## Path aliases

An alias followed by a relative path means their literal concatenation. The
inventory tables below enumerate exact paths using these aliases; no wildcard
authorizes additional inspection.

| Alias | Exact path |
| --- | --- |
| R | `C:\Users\Data Viz\Desktop\Anderson_Hail\bsfm-spatial-transcriptomics` |
| E | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CURRENT_20261014\bayesian_spatial_factor_model` |
| P | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_19_SECTION_PRODUCTION_20261024` |
| C | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030` |
| CS | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030\source_snapshot` |
| CC | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030\source_snapshot\code` |
| CA | `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_CONSOLIDATION_20261030\bsfm_cleanup_audit_20261030` |
| Z | `C:\Users\Data Viz\Downloads\BAYESIAN_SPATIAL_FACTOR_MCMC_20261014.zip` |

Referenced HPC roots, not accessed during B1/B2:

| Alias | Exact path |
| --- | --- |
| H-E | `/work/abussing/arka_trying_gpu_again/zeta_n300_L16_v1` |
| H-P | `/work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024` |
| H-C | `/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1` |

## User decisions and repository context

| ID | Source | Class and relevance |
| --- | --- | --- |
| U1 | User's Stage A refinements in this recovery conversation | User decision: log1p(corrected counts) is the stated scientific intent; recover its meaning and consumption without reopening the scale decision because of older residual-based candidates. |
| U2 | User's B1/B2 approvals and B2 conditions in this conversation | User decision: bounded read-only evidence recovery; hash six sources before reading; inspect driver input boundaries; do not run models, select/import implementations or follow new upstream references. |
| U3 | User's checkpoint request in this conversation | User decision: persist B1/B2 only, update the capability status minimally, and make/push one focused documentation commit. |
| R1 | `R/AGENTS.md` | Repository rules: provenance before selection, explicit evidence types, no unapproved HPC jobs, no large scientific artifacts in Git. |
| R2 | `R/README.md` | Repository context: historical recovery, no frozen production implementation. |
| R3 | `R/CAPABILITIES.md` | Required preprocessing and identity/version preservation; initial tentative response wording is clarified by U1. |
| R4 | `R/docs/RECOVERY_PROCESS.md` | Recovery process: purpose, lineage, artifact tracing, evidence distinctions and unresolved choices before selection. |

Conversation instructions are recorded by topic rather than an invented message
identifier. No exported historical user conversation was inspected in B1/B2.

## B1 inspected-source inventory

All following metadata were read as data. Reading an index containing source
names or function names did not constitute reading those implementation files.
No archive member contents were read. Directory listings were used only for
navigation and file metadata.

The following seven relative files were inspected at **each of E, P and CC**
(21 exact file paths). Their text compared equal across the three locations.

| Relative file | Class and relevant content |
| --- | --- |
| `MANIFEST.json` | Documentation claim: 71 base-package path/hash entries; retains the base driver hash. |
| `FILE_INDEX.json` | Documentation claim/navigation: function/class names and line numbers, including GPINIT main at 42 and base driver main at 264. |
| `provenance/ENVIRONMENT.json` | Documentation claim: recorded Python environment; does not supply R/Seurat/sctransform versions. |
| `provenance/INPUT_OUTPUT_SCHEMAS.json` | Documentation claim: simulation truth/GPINIT/checkpoint schemas; Y is 32 x 2500 in the example, not evidence of real-data response scale. |
| `provenance/ORIGINAL_STUDY_MANIFEST.json` | Documentation claim: original study source/artifact hashes; no artifacts opened or rehashed. |
| `provenance/RECORDED_COMMAND.json` | Execution evidence with limit: recorded simulation invocation under H-E, using truth.npz and gpinit.npz; not a real-data preprocessing execution receipt. |
| `provenance/SOURCE_SNAPSHOT.json` | Documentation claim/provenance: H-E export root, retrieval time, source paths, sizes and recorded original-manifest matches. |

Additional inspected metadata (exact paths):

| Path | Inspection and evidence classification |
| --- | --- |
| `E/START_HERE.txt` | Documentation claim: source-and-method handoff, 57 original source matches, excluded data/GPINIT/checkpoints, historical workflow paths. |
| `E/RUNNING_AND_VALIDATION.txt` | Documentation claim/downstream consumption: genes x cells Y, matching GPINIT and geometry requirements; says no full fit was run to create the package. |
| `E/VALIDATION.json` | Execution evidence: recorded syntax/unit/toy checks and their exclusions; no SCTransform or real-data reproduction validation. |
| `E/CURRENT_MODEL_AND_UPDATES.txt` | Targeted keyword/context excerpts only. Lines 4-6 claim driver within-type gene centering; 137-143 describe GPINIT input fields. Response-related search also returned contextual model descriptions; no source algorithms were followed from them. |
| `P/BSFM_ANALYSIS_ROADMAP.md` | Documentation claim: common panel, biological units and required immutable input sidecars; not proof of actual preprocessing. |
| `P/PRODUCTION_OVERLAY_README.md` | Documentation claim: E base and a retention-only driver extension. |
| `P/PRODUCTION_CODE_MANIFEST.json` | Documentation claim: E base, old/new driver hashes, 17 additions, and re-adaptation in addition to retention. |
| `P/PRODUCTION_LAUNCH_CONTRACT.json` | Execution evidence with limit: records pilot job IDs and passing checks; not the underlying certificates or proof of the SCTransform chain. |
| `P/PRODUCTION_RETENTION_CONTRACT.json` | Documentation claim/downstream consumption requirements: modeled expression, ordering, transformations, centering and immutable inputs. |
| `C/README.md` | Documentation claim: partial local copy of H-C code/manifests and collected HPC inventories. |
| `C/CLEANUP_FINDINGS.md` | Documentation claim: prepared package versus older campaign, reported GPINIT success and conflicting run specifications; claims of authority remain historical claims. |
| `C/REQUEST_TRACE_HOLE_CV.md` | Documentation claim: historical request trace and input-leakage concerns; no referenced prediction/analysis implementation inspected. |
| `C/RUN_SPEC_TO_DECIDE.md` | Documentation claim: unresolved scientific/run settings, not a settled preprocessing decision. |
| `C/TARGET_LAYOUT.md` | Documentation claim: proposed layout and provenance requirements, not actual artifact lineage. |
| `CS/README_L4.txt` | Documentation claim: 19 sections, 91 genes, 20 factors, 50% within-type selection and fresh GPINIT; preliminary panel. |
| `CS/BUNDLE_MANIFEST.json` | Documentation claim: code, observation, GPINIT and certificate path/hash records; compared with other recorded manifests. |
| `CS/SOURCE_MANIFEST.json` | Documentation claim: copied code and source_geometry paths/hashes; 106 paths shared with bundle manifest have matching recorded hashes. |
| `CS/INPUTS_MANIFEST.json` | Documentation claim: 19 records with source/output hashes and expression described as same transformed data, re-centered within retained cell type. |
| `CS/PACKAGE_RESULT.json` | Execution evidence with limit: reports CPU validation and GPINIT passed, READY_FOR_CLOUD_GPU_PREFLIGHT, GPU_smoke_run=false; underlying certificates unread through B2. |
| `CC/PRODUCTION_OVERLAY_README.md` | Documentation claim: inherited overlay description, not independent confirmation. |
| `CC/PRODUCTION_CODE_MANIFEST.json` | Documentation claim: inherited base/change/addition record, not independent confirmation. |
| `CA/new_key_sha256.txt` | Documentation claim/provenance: historical hashes of selected package files; no new hashing during B1. |
| `CA/old_root_top_level.txt` | Inventory evidence: recorded H-P top-level names, including input/run variants; those directories were not accessed. |
| `CA/new_root_file_inventory.tsv` | Initial rows and targeted preprocessing/input/certificate/manifest/GPINIT matches only. Records artifact names, sizes and timestamps; no artifact contents inspected. |
| `Z` | Central-directory listing only: 72 file paths, compressed/uncompressed sizes. Corresponding E paths exist and match uncompressed sizes. Neither ZIP contents nor ZIP hash checked. |

Immediate `study_workflow` listings under E/P contained implementation files and
no separate documentation files. No study-workflow implementation was read.
The `CS/inputs` and `CS/source_geometry` directories were absent in the local
snapshot. Remote existence was not tested through B2.

## B2 measured source identities

SHA-256 and size were measured before reading these six sources. No two files in
this set are byte-identical. Their measured hashes agree with previously inspected
manifest records. Copies elsewhere remain manifest-reported duplicates, not
additional measured implementations. No large data/archive/serialized object was
hashed.

| ID | Exact aliased path | Bytes | Measured SHA-256 |
| --- | --- | ---: | --- |
| A | `P/production/prepare_sections.py` | 7609 | `c6fbec4f619e7fa65a8fbcea38da893a746af6c1124e5dbda116b1ad620c3248` |
| B | `CS/prepare_inputs.py` | 5797 | `5589abd66ddc5dea3c186e426653a50620643c7c47f5b4303382a0c43e38ae13` |
| C | `P/production/prepare_one_section.sh` | 1800 | `d0cf0a39d2e72d55735b3945fdec7250fcd042ca23053cd59ac2d0eae9e2e0a5` |
| D | `P/sampler/build_gpinit_from_truth_npz.py` | 8433 | `f5b1545072c462cf772cd3caf44a398da8cf5558b4a2dd3133922c8cd8143f94` |
| E | `P/sampler/run_c3full_fixed_profile_nuts.py` | 94890 | `eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49` |
| F | `E/sampler/run_c3full_fixed_profile_nuts.py` | 92894 | `3e81660c6d5e8772a35bfb2cc18a75988c26f6ac0fd7dd2c63e58a1d2859ac79` |

File IDs E/F are source identifiers; path alias E still denotes the base directory.

## B2 claim-to-source ledger

| Evidence | References | Classification and limit |
| --- | --- | --- |
| Source artifact keys/path | A:30-49 | Implemented behavior/downstream consumption: reads screen section Y/raw and metadata. Actual screen root unknown through B2. |
| Panel and ordered cells | A:14-15,34-80 | Implemented behavior: panel lookup, availability checks and stable type grouping with consistent identity permutation. |
| Prepared response | A:79-92,101-134 | Implemented behavior: float64 genes x cells, within-type gene centering, exported Y and separate incoming-expression/raw-count sidecar. |
| Claimed SCT response | A:148 | Documentation claim embedded in generated contract: SCT v2 log1p. No SCTransform or response log call in A. |
| Production handoff | C:15-28 | Implemented/configured downstream consumption: builder then observation-to-GPINIT invocation; no execution proof or transfer-builder inspection. |
| Retained-cell selection | B:17-24,35-48,60-62 | Implemented behavior: spatial ordering, every-other-cell selection within type, sorted retained indices and paired metadata subset. |
| Retained-cell centering/export | B:63-76 | Implemented behavior: subtract retained means, accumulate shifts, set 20 factors, export Y. Does not establish historical artifact equality. |
| GPINIT response construction | D:49-66 | Implemented behavior: only Y/coordinates/type IDs read; float64 copy and within-type centering. D:60's runner-equivalence comment is a documentation claim. |
| GP fitting and seed-only transforms | D:79-96,120-132,167-177 | Implemented behavior: nfit subset, normalize_y=True, predicted-field centering and SVD seeds. No replacement response export. |
| Diagnostic record schema | D:178-201 | Implemented behavior: records input path/hash, dimensions, nfit and maximum_input_recentering_mean. Historical values unread through B2. |
| Driver observation boundary | E:328-368 / F:323-363 | Implemented behavior/downstream consumption: input loading and checks, no response centering. Aligned blocks are text-identical. |
| Driver GPINIT boundary | E:468-480 / F:463-475 | Implemented behavior/downstream consumption: seed loading and shape checks. Aligned blocks are text-identical; source identity/value equality not checked there. |
| Driver response references | E:336,340,358,493-496; F:331,335,353,488-491 | Focused response-reference search found no response-centering assignment in either driver. Referenced helper algorithms were not followed. |
| CLI/default distinction | A:178-181; C:17,23-27; D:208-213; E:1715-1721 / F:1684-1690 | Implemented/configured behavior: required paths, defaults, wrapper overrides, opt-in real-data mode; does not establish actual production arguments. |
| Centering idempotence/subsetting identity | Deductions from A:83-90, B:60-69, D:62-66 | Mathematical deduction from implemented behavior: same-group centering is idempotent in exact arithmetic; subset re-centering equals directly centering retained original expression. Not empirical validation. |

Drivers were inspected through targeted input/response/GPINIT excerpts and
response-reference searches, with an aligned comparison of the boundary blocks.
No unrelated sampler helper was imported or executed. The other four approved
sources were read; only preprocessing/handoff behavior is used in this recovery.

## Lineage and evidence limits

| Relationship | Basis | Limit |
| --- | --- | --- |
| Z and E | 72 ZIP member paths have corresponding E files with matching lengths. | Size/name agreement does not prove byte identity; no extraction or member read. |
| E to P | P overlay manifest names E, records base/production driver hashes and 17 additions. | Labels and recorded lineage are not scientific validation. |
| E to CC | 70/71 base-manifest hashes match CS bundle entries. The changed driver matches the declared overlay hash. | Recorded manifest comparison; only B2's six files freshly hashed. |
| P to CC | All 17 listed overlay-addition hashes and the production-driver hash match CS bundle records. | Does not prove complete current-directory identity. |
| H-C to CS | C README and inventories describe copying package code/manifests; manifests reference input and certificate artifacts. | A partial local snapshot, not a complete runnable/input package. |
| Historical GPINIT execution | CS package result reports success; inventory records outputs/certificates. | No SCTransform execution proof or exact candidate-to-run attribution. |
| Historical sampler consumption | H-E recorded simulation command and P pilot-check claims. | No established real-data observation/GPINIT pairing for a production invocation. |

## Contradictions and unresolved gaps

- **Unresolved gap:** `E/CURRENT_MODEL_AND_UPDATES.txt:4-6` and D:60 describe
  runner centering; E/F's inspected behavior does not implement it.
- **Unresolved gap:** A:148's SCT-v2-log1p assertion lacks an identified upstream
  SCTransform/export implementation or R package provenance through B2.
- **Documentation discrepancy:** inherited base manifest records the old driver,
  while the overlay and bundle record the changed driver. They describe different
  layers and must not be collapsed into a single complete-file inventory.
- **Documentation discrepancy:** overlay README says retention-only; overlay
  manifest also records re-adaptation. No response change follows from this alone.
- **Unresolved gap:** input export status versus later package success may be
  staged evidence; underlying certificates and actual residuals were not read.
- **Unresolved gap:** the production base-to-observation builder, consolidation
  preparation wrapper and actual sampler launch paths were outside B2.
- **Unresolved gap:** no numerical artifact comparison, all-section consumption
  audit, package-version reconstruction, or scientific response certification was
  completed through B2.

## Follow-up references identified, not inspected through B2

| Exact path or parameterized family | Question |
| --- | --- |
| `P/production/build_section_mesh.py` | Does the observation transfer preserve Y and identities? Read only that boundary. |
| `CS/prepare_cpu.sh` | Which observation artifact/settings reach consolidation GPINIT? |
| `CS/run_cloud.sh` | Where is the sampler command constructed? Follow no new implementation automatically. |
| `H-P/inputs/INPUT_PREPARATION_CONTRACT.json` | What source paths, gene order and section registry were recorded? |
| `H-P/inputs/sections/<section>/INPUT_CONTRACT.json` | Which upstream input and base-output hashes/configuration were recorded? |
| `H-P/inputs/sections/<section>/gpinit/GPINIT_CERTIFICATE.json` | What input hash, dimensions and centering residual were measured historically? |
| `H-C/source_geometry/<section>/INPUT_CONTRACT.json` | What upstream source supplied the copied base input? |
| `H-C/inputs/<section>/INPUT_CERTIFICATE.json` | What source/output hashes and retained-cell convention were recorded? |
| `H-C/inputs/<section>/gpinit/CERTIFICATE.json` | Does GPINIT identify the intended retained observation input? |
| `<historical --screen-root>/sections/<section>/input.npz["Y"]` | What upstream code wrote Y, and which corrected-count object and log transform did it use? Do not open/hash the matrix to substitute for provenance recovery. |

These follow-up references preserve the B2 stopping point. Later evidence belongs
in a separately identified checkpoint. No legacy source, credentials, raw data,
matrix, environment, checkpoint or posterior draw is stored here.
