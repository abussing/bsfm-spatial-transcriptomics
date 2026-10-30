# SCTransform evidence ledger through Stage B5/B5b

Checkpoint date: 2026-10-30. Scope: B1 metadata/provenance, B2 six-file source
inspection, accepted B3 local handoff/HPC metadata, and the accepted incomplete
B4 exporter/provenance increment, and the accepted B5/B5b bounded search endpoint.
B1/B2 remain available at
`d2e7e5ea9db420fe2910cd54ac1e33040a0726db`; B3 at
`71a7dcad7a2252157c7cd8e83bfb4bdd9a6b3b7a`; B4 at
`b746b41784e09c6223874e90f3103c5e86c913a9`. Earlier-stage sections retain their
stage-specific limits. No implementation has been selected. No HPC reconnection
or broader search was made to preserve this checkpoint. Replacement design is
not yet approved. Historical normalization and branch comparability remain unresolved.

During checkpoint preparation the user attached the historical drive. All five
known paths became accessible on D:, while E: remained unavailable. Only exact
path checks were performed. This new availability supersedes the current-access
conclusion of the earlier search, not its recorded negative observations.
Historical labels such as CURRENT and PRODUCTION confer no authority.

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

B3 identifies H-U as
`/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1`.
H-U was referenced by returned contracts but was not accessed during B3. B4's
bounded inspection of that root is recorded in the appended ledger below.

## User decisions and repository context

| ID | Source | Class and relevance |
| --- | --- | --- |
| U1 | User's Stage A refinements in this recovery conversation | User decision: log1p(corrected counts) is the stated scientific intent; recover its meaning and consumption without reopening the scale decision because of older residual-based candidates. |
| U2 | User's B1/B2 approvals and B2 conditions in this conversation | User decision: bounded read-only evidence recovery; hash six sources before reading; inspect driver input boundaries; do not run models, select/import implementations or follow new upstream references. |
| U3 | User's checkpoint request in this conversation | User decision: persist B1/B2 only, update the capability status minimally, and make/push one focused documentation commit. |
| U4 | User's B3 approval and subsequent B3 acceptance/checkpoint request | User decision: read bounded local handoffs and named HPC metadata for all 19 sections; accept the existing concrete report; preserve captures, validate and commit B3 without reconnecting. |
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

## B1/B2 contradictions and unresolved gaps

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

These follow-up references preserve the B2 stopping point. The B3 increment below
records subsequent inspection. No legacy implementation, credentials, raw data,
matrix, environment, checkpoint or posterior draw is stored here.

## B3 capture preservation and validation

The user accepted the B3 report and requested preservation without another HPC
connection. Existing temporary captures were read, validated and copied into
[evidence/sctransform_b3/](evidence/sctransform_b3/). These are metadata stdout
captures, not terminal-session logs or remote file-byte snapshots.

Original location for all three:
`C:\Users\Data Viz\AppData\Local\Temp\`.
The acquisition environment also reported its equivalent short path
`C:\Users\DATAVI~1\AppData\Local\Temp\`.

| Original temporary basename | Preserved file | Bytes | Measured capture SHA-256 |
| --- | --- | ---: | --- |
| bsfm-b3-s00-metadata.txt | [s00_and_preparation_summary.txt](evidence/sctransform_b3/s00_and_preparation_summary.txt) | 74706 | e5f049a487a68c38d04873855b54df0b5042b1ebe8c0d10998a7369ff3f8b008 |
| bsfm-b3-all19-metadata.txt | [all_19_section_contracts_and_certificates.txt](evidence/sctransform_b3/all_19_section_contracts_and_certificates.txt) | 444006 | 7fe50386f3660c2b7ed60e9d3f5517c096c57373c597823fc9948d5c1eeb7717 |
| bsfm-b3-package-metadata.txt | [package_manifests_and_launch_contract.txt](evidence/sctransform_b3/package_manifests_and_launch_contract.txt) | 157048 | 25a9e7b01d2a0d4a543c584434ba82b4a10971c9ef3278d4a560880b54ee3b81 |

Combined size: **675760 bytes**, below 2 MiB (2097152 bytes).
All files retain their original UTF-16LE BOM/encoding and line endings.
A directory-local `.gitattributes` sets `*.txt -text` to prevent Git text
conversion. Copy hashes were verified equal to the temporary originals.
These capture hashes must not be confused with artifact hashes inside the JSON,
which remain historical records and were not freshly measured from large arrays.

| Capture | Complete JSON records | Explicit MISSING records | Largest untrimmed captured body, UTF-8 bytes including separators |
| --- | ---: | ---: | ---: |
| S00/summary | 6 | 1 | 25498 |
| All sections | 95 | 19 | 3344 |
| Package | 5 | 1 | 49312 |

All **106 returned JSON records parsed completely** using strict JSON decoding
that rejects trailing non-whitespace content, duplicate object keys and
nonstandard numeric constants. The other 21 results are explicit MISSING
markers, not malformed JSON. Repeated paths have identical parsed values.
There are 101 unique returned metadata files and 20 unique missing paths.

No captured body reached the 131073-byte head limit. The comparison includes
untrimmed body text and separator newlines, so it is conservative for these ASCII
JSON bodies; capture encoding/Windows line endings can enlarge their UTF-8
representation relative to remote stdout. Every returned body is well below
the limit and parses fully. Remote stat sizes and original remote file bytes
were not separately recorded, so the preserved hashes identify captures only.

Credential/authentication review found no password, passphrase, private-key,
authorization-header, bearer-token, API-key, access/refresh-token or client-secret
pattern; there are no terminal escape sequences or authentication prompts.
All content consists of approved-path markers, JSON metadata or MISSING.
Usernames in provenance paths and scientific hashes are retained as provenance,
not secrets. Authentication input was not part of these stdout captures and is
not included in acquisition documentation.

## B3 exact sources and inspection boundary

Local paths use the aliases above. These three sources were read during B3;
they were not executed or copied into the repository.

| Local source | Exact inspection | Class and finding |
| --- | --- | --- |
| `P/production/build_section_mesh.py` | Targeted locators; numbered excerpts 104-125,251-268,283-311; later narrowed to 111-113,251-258,296,307-311. Some adjacent geometry statements appeared in excerpts. | Implemented behavior: reads all base arrays and exports them with added geometry fields; no response transformation or cell/gene selection at this boundary. No geometry routine executed. |
| `CS/prepare_cpu.sh` | All 17 lines. | Configured downstream consumption: lines 13-16 specify observation-to-GPINIT paths, 20 factors, nfit=250 and seed=2026102600 + index. Not proof of the exact historical command execution. |
| `CS/run_cloud.sh` | All nine lines. | Implemented handoff: line 9 delegates to cloud_run.py. That implementation was not followed; actual sampler command remains unresolved. |

The source versions were not newly hashed or snapshotted during B3. B3 statements
about them rely on the recorded local inspection; no assertion of identity with
an executed HPC source version follows automatically.

For every one of the 19 exact `section_id` values in
[SCTRANSFORM_B3_SECTIONS.csv](SCTRANSFORM_B3_SECTIONS.csv), these paths were queried:

| Path family | Result | Class |
| --- | --- | --- |
| `H-P/inputs/sections/<section_id>/INPUT_CONTRACT.json` | 19 read | Historical documentation/execution record: upstream path/hash, base hash, counts, factors, ordering, transformation claim. |
| `H-P/inputs/sections/<section_id>/mesh/MESH_CERTIFICATE.json` | 19 read | Historical execution record: output observation hash and cell count; geometry fields were not independently tested. |
| `H-P/inputs/sections/<section_id>/gpinit/GPINIT_CERTIFICATE.json` | 19 read | Historical execution/consumption record: input path/hash, dimensions, factors, nfit, residual and PASS. |
| `H-C/source_geometry/<section_id>/INPUT_CONTRACT.json` | 19 missing | Unresolved gap; matching source/base hashes provide an alternate recorded link. |
| `H-C/inputs/<section_id>/INPUT_CERTIFICATE.json` | 19 read | Historical input record: source/output hashes, type counts, retained selection/re-centering convention. |
| `H-C/inputs/<section_id>/gpinit/CERTIFICATE.json` | 19 read | Historical execution/consumption record: input path/hash, dimensions, factors, nfit, residual and PASS. |

Additional exact HPC paths:

| Path | Result and relevance |
| --- | --- |
| `H-P/inputs/INPUT_PREPARATION_CONTRACT.json` | Read; complete common 91-gene order, section registry, 19 individual contract entries and 15 distinct mice. |
| `H-P/PRODUCTION_LAUNCH_CONTRACT.json` | Missing at this location. |
| `H-P/code/PRODUCTION_LAUNCH_CONTRACT.json` | Read; launch settings and pilot claims, not each executed command. |
| `H-C/SECTIONS.json` | Read; agrees with the production section order. |
| `H-C/PACKAGE_RESULT.json` | Read; package success claim and GPU_smoke_run=false. |
| `H-C/SOURCE_MANIFEST.json` | Read; 220 recorded entries, mapping agrees with the previously collected local manifest. |
| `H-C/BUNDLE_MANIFEST.json` | Read; 441 recorded entries, mapping agrees with the local manifest and includes all 19 retained GPINIT output hashes. |

Every exact upstream path is in the CSV's `source_input_path` column and equals
`H-U/sections/<section_id>/input.npz`. H-U was discovered, not inspected.
No recursive directory search, array read, scientific execution, submission or
HPC modification was performed. No connection was made when preserving this
checkpoint.

## B3 acquisition commands

These commands document the prior acquisition; they are not instructions to rerun
it. Authentication input is intentionally absent.

The first successful read, on SSH port 222, was:

```powershell
& 'C:\Windows\System32\OpenSSH\ssh.exe' -p 222 -o ConnectTimeout=20 -o ServerAliveInterval=15 -o StrictHostKeyChecking=yes abussing@login.rci.sc.edu 'cat /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/inputs/sections/S00__Trem2_5xFAD4/INPUT_CONTRACT.json'
```

Its terminal output wrapped long lines, so the capture below is used for exact
values. Three subsequent calls used this invocation form, substituting each
literal capture basename and the exact remote body below:

```powershell
$metadataOutput = Join-Path $env:TEMP '<capture-basename>'
& 'C:\Windows\System32\OpenSSH\ssh.exe' -p 222 -o ConnectTimeout=20 -o ServerAliveInterval=15 -o StrictHostKeyChecking=yes abussing@login.rci.sc.edu '<remote-body>' > $metadataOutput
Write-Output "Metadata capture: $metadataOutput"
```

For `bsfm-b3-s00-metadata.txt`, the remote body was:

```sh
for f in /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/inputs/INPUT_PREPARATION_CONTRACT.json /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/inputs/sections/S00__Trem2_5xFAD4/INPUT_CONTRACT.json /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/inputs/sections/S00__Trem2_5xFAD4/mesh/MESH_CERTIFICATE.json /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/inputs/sections/S00__Trem2_5xFAD4/gpinit/GPINIT_CERTIFICATE.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/source_geometry/S00__Trem2_5xFAD4/INPUT_CONTRACT.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/inputs/S00__Trem2_5xFAD4/INPUT_CERTIFICATE.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/inputs/S00__Trem2_5xFAD4/gpinit/CERTIFICATE.json; do echo BSFM_FILE:$f; if test -f $f; then head -c 131073 $f; else echo MISSING; fi; echo; done
```

For `bsfm-b3-all19-metadata.txt`, the remote body was:

```sh
p=/work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024; c=/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1; for s in S00__Trem2_5xFAD4 S01__5xFAD4 S02__Trem2_4 S03__Trem2_5xFAD3 S04__WT3 S05__Trem2_3 S06__5xFAD3 S07__Trem2_5xFAD5 S08__5xFAD5 S09__Trem2_5 S10__WT5 S11__Trem2_5xFAD1 S12__Trem2_1 S12__Trem2_5xFAD2 S13__Trem2_2 S14__WT1 S15__5xFAD1 S16__WT2 S17__5xFAD2; do for f in $p/inputs/sections/$s/INPUT_CONTRACT.json $p/inputs/sections/$s/mesh/MESH_CERTIFICATE.json $p/inputs/sections/$s/gpinit/GPINIT_CERTIFICATE.json $c/source_geometry/$s/INPUT_CONTRACT.json $c/inputs/$s/INPUT_CERTIFICATE.json $c/inputs/$s/gpinit/CERTIFICATE.json; do echo BSFM_FILE:$f; if test -f $f; then head -c 131073 $f; else echo MISSING; fi; echo; done; done
```

For `bsfm-b3-package-metadata.txt`, the remote body was:

```sh
for f in /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/PRODUCTION_LAUNCH_CONTRACT.json /work/abussing/arka_trying_gpu_again/bsfm_19section_production_20261024/code/PRODUCTION_LAUNCH_CONTRACT.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/SECTIONS.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/PACKAGE_RESULT.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/SOURCE_MANIFEST.json /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/BUNDLE_MANIFEST.json; do echo BSFM_FILE:$f; if test -f $f; then head -c 131073 $f; else echo MISSING; fi; echo; done
```

Each body above was passed as one single-line SSH command. The remote operations
were test/head/cat and output markers; no project script was invoked.
Two earlier attempts on default port 22 failed before authentication and yielded
no remote metadata; an `ssh -G` diagnostic inspected effective connection
settings. The successful connection used the user-specified port 222.
No credentials or authentication transcript are preserved here.

Local inspection used these data-reading expressions (presentation labels omitted):

```powershell
$base = 'C:\Users\Data Viz\Desktop\Anderson_Hail'
$mesh = Join-Path $base 'BSFM_19_SECTION_PRODUCTION_20261024\production\build_section_mesh.py'
Select-String -LiteralPath $mesh -CaseSensitive -Pattern 'np.load|np.save|OBSERVATIONS|cell_id|gene_names|cell_names|source_row|centering|data\[|data\.|\bY\b|contract|certificate|sha256|section_dir' | ForEach-Object { '{0}: {1}' -f $_.LineNumber, $_.Line }
foreach ($relative in @('BSFM_CONSOLIDATION_20261030\source_snapshot\prepare_cpu.sh','BSFM_CONSOLIDATION_20261030\source_snapshot\run_cloud.sh')) {
 $n=0
 Get-Content -LiteralPath (Join-Path $base $relative) | ForEach-Object { $n++; '{0}: {1}' -f $n,$_ }
}
$path = 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_19_SECTION_PRODUCTION_20261024\production\build_section_mesh.py'
$lines = [System.IO.File]::ReadAllLines($path)
foreach ($range in @(@(104,125),@(251,268),@(283,311))) {
 for ($i=$range[0]; $i -le $range[1]; $i++) { '{0}: {1}' -f $i,$lines[$i-1] }
}
Select-String -LiteralPath $path -CaseSensitive -Pattern '\bbase\b|\bobservations\b|\bobs\b|\by\b|\bcell_id\b|\bsource\b' | ForEach-Object { '{0}: {1}' -f $_.LineNumber,$_.Line }
```

The final local excerpt pass used the same numbered-line loop with ranges
`@(111,113),@(251,258),@(296,296),@(307,311)`.
Temporary captures were read with `Get-Content -LiteralPath ... -Raw`, parsed as
JSON locally and compared in memory. Those analysis operations did not reconnect.

## B3 machine-readable audit and findings

[SCTRANSFORM_B3_SECTIONS.csv](SCTRANSFORM_B3_SECTIONS.csv) is derived from the
preserved captures, one row per section in the recorded registry order. It stores:

- upstream path/hash; full and retained cell counts, genes and type counts;
- factor counts, nfit, historical residuals and GPINIT certificate statuses;
- both sides of the base/source and observation/GPINIT-source hash comparisons;
- retained GPINIT output hashes from the bundle manifest;
- source-path, hash-link and dimension match flags;
- missing copied-source-contract and unresolved sampler-consumption status.

Booleans are serialized as True/False. All `*_match` fields are True for all
19 rows. `copied_source_contract_present` is False for all rows.
`sampler_consumption_status` is `not_established`, not a claim that consumption
failed. Empty `full_gpinit_artifact_sha256` means that an output hash for the
full-cell GPINIT artifact was not recovered; it must not be filled with its
input/source hash. Every other stored SHA-256 is a historical recorded hash;
the new capture hashes above are a separate category.

The CSV's expected paths are defined by the exact queried families above.
Full GPINIT source hashes are compared with mesh certificates; retained GPINIT
source hashes with retained input certificates; retained source-base hashes with
production input contracts. Counts/factors/genes are compared between input and
GPINIT records. The preparation summary's gene order is preserved in the S00
capture; per-artifact gene/cell identifier arrays were not inspected.

S00 (`S00__Trem2_5xFAD4`) illustrates the recorded chain:

| Artifact | Recorded SHA-256 |
| --- | --- |
| H-U input.npz | 931ef86d56c64d55f3aa81318201f99d8ed97ffa81b1ff4b04e24b66486ceaa5 |
| H-P OBSERVATIONS_BASE.npz / H-C source base | b45650cc62500cccddbcffc1c6f7626c088cdbaa8908603b43436774f9d7b094 |
| H-P OBSERVATIONS.npz / full GPINIT source | 9ba31f6b92112cdfae486480117a37b49eff4a2e635cba3269514b42a1ceb217 |
| H-C OBSERVATIONS.npz / retained GPINIT source | b40a3b7b2195e4ed0c00df1a858a4a5ee187fc2a3803b544bd6fdac52e62e6cb |
| H-C gpinit/gpinit.npz | 8fa32af999f125d597dd903da99a6b621923a0f7235f82fa99d5f64fbadf4df0 |

All 19 rows establish the same kinds of recorded link, independently of S00.
No large-array current-byte equality was measured.

### Recorded settings versus supported settings

All full-cell GPINIT records: 91 genes, three types, 25 factors, nfit=250.
All retained-cell GPINIT records: 91 genes, three types, 20 factors, nfit=250.
Seed formulas occur in wrappers, not the GPINIT certificates. B2 default values
(5 factors, nfit=500, seed=0) are not substituted for recorded settings.

The production launch contract records four chains/section and 25 factors.
Stage 1 specifies 100 adaptation transitions per factor, 100 discarded bridge
sweeps and target acceptance 0.9. Stage 2 specifies complete checkpoint
restoration, 100 adaptation transitions per factor, target acceptance 0.95,
100 discarded settling sweeps, 1000 retained sweeps, full state every five
sweeps and checkpoint every sweep. These are contract settings, not recovered
executed commands.

The contract records mechanical jobs 21993432/21993433, pilot jobs
21993445/21993446, pilot checks PASS, zero production divergences, maximum
independent covariance-entry error 1.7763568394002505e-15 and warp-projector error
2.220446049250313e-16. Those are historical summary claims, not independently
read per-run certificates. H-C's package result records
READY_FOR_CLOUD_GPU_PREFLIGHT and GPU_smoke_run=false, not completed sampling.

### Conclusions, gaps and B4 boundary

Directly observed: returned records, missing-path results, static local source
behavior, complete JSON parsing, capture byte hashes and field comparisons.

Historical measurements: artifact hashes, dimensions, residuals and statuses
inside certificates. They were not recalculated from NPZ content.

Inference: the maximum residuals (7.79803603973186e-14 full,
1.0826147601551898e-14 retained) are consistent with floating-point residue.
Together with inspected code, this supports numerical equivalence of already
centered observations and GPINIT's extra centering. It is not a bitwise-array
comparison or scientific response certification.

Outstanding gaps:
- corrected-count assay/slot/layer, actual SCTransform/v2 arguments and versions;
- upstream raw-input filtering, log1p placement and execution/export provenance;
- copied H-C source contracts (19 missing) and full GPINIT output-to-run hashes;
- actual sampler commands and paired observation/GPINIT input manifests;
- independent verification of live large-artifact bytes and ordered identities.

The export-status/GPINIT-PASS distinction describes different stages; it does
not alone imply a contradiction. The inherited driver-centering documentation
discrepancy remains. This audit concerns the full-cell/25-factor and retained-cell/
20-factor branches, not every historical campaign.

B4 is proposed, not performed: one nonrecursive listing of H-U and H-U/audit;
small provenance/index/README records and `H-U/audit/SECTIONS.csv`; then only
the identified SCTransform invocation and exporter writing `input.npz["Y"]`,
with directly referenced version/execution evidence across all 19 sections.
Exact upstream script names are unknown. NPZ/RDS/Seurat objects remain unopened
and unhashed. A separate expansion would be needed to inspect cloud_run.py's
response paths and locate actual sampler run-command records.

No implementation is selected or imported. Neither the upstream SCTransform
step nor actual sampler invocation is certified by this checkpoint.

## B4 capture preservation and validation

User decision U5: B4 was approved as bounded read-only upstream recovery, then
accepted as an incomplete checkpoint. Preserve evidence and commit before B5.
The user resolved the capture/code conflict explicitly: commit the three
metadata-only captures and preserve the two source-text captures outside Git in
the specified stable evidence directory. No HPC connection, historical program
execution or further upstream inspection was performed to prepare this commit.

**review.py does not itself implement SCTransform. sct_section.R is missing from
the inspected package. Readiness records can reuse preexisting CSVs. Nine reused
historical exports have separate unrecovered normalization implementations.
Comparability across the ten-new/nine-reused branches is not established.
log1p(corrected counts) remains the scientific intent, not a certified fact about
every historical section.** No implementation is selected or imported.

All original capture basenames below were in
`C:\Users\Data Viz\AppData\Local\Temp\` (also exposed as the equivalent short
path `C:\Users\DATAVI~1\AppData\Local\Temp\`). Copies preserve their UTF-16LE
encoding/BOM and original bytes. The measured SHA-256 values below identify
captures, not source files or scientific artifacts inside them.

| Original basename | Preserved location | Bytes | Capture SHA-256 |
| --- | --- | ---: | --- |
| bsfm-b4-root-listing.txt | [Git: root listing](evidence/sctransform_b4/bsfm-b4-root-listing.txt) | 2938 | ac89b61748b25593e1b2b5d5c68c220dab0a4dad8c7dde4a435ab7a053c1a5f0 |
| bsfm-b4-root-metadata.txt | [Git: README and indexes](evidence/sctransform_b4/bsfm-b4-root-metadata.txt) | 121256 | ceb96e0967a6b307eaa3486f1f56cd397ca1e164cbb492ca8833c5b15aae5b59 |
| bsfm-b4-readiness-and-source-index.txt | [Git: readiness records and source hash](evidence/sctransform_b4/bsfm-b4-readiness-and-source-index.txt) | 33896 | 5a4699bcb15757276fd61a750d26ce77e5d2585a64fb6b9e4c0ae88c5964d9f4 |
| bsfm-b4-source-declarations.txt | External path D below | 2892 | e142643c73f9a7c2ec75c638b760fc5073802e95fadeb2fb3f0dc60845f9683f |
| bsfm-b4-preparation-source-excerpt.txt | External path X below | 19484 | 3a4140ada8241aecad31b4702bd4c0754a38caff471f8c19114535a96ab06da3 |

Exact stable external paths (outside the repository, not included in its Git backup):

- D: `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\sctransform_b4\bsfm-b4-source-declarations.txt`
- X: `C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\sctransform_b4\bsfm-b4-preparation-source-excerpt.txt`

Both originate from
`/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1/review.py`.
D contains locator matches at lines 19-22,24-25,29,31,33,39,67,139,167,215,248,279,281.
Line 279 is an incidentally returned display-style constant; unrelated function
bodies were not inspected. X contains exactly numbered lines 1-138, including
preparation, candidate construction, helpers and imports. The remaining script
was not captured. The full small source was hashed, not executed.

Combined capture size is **180466 bytes**, below 2 MiB. The three Git captures
total 158090 bytes; the two external captures total 22376 bytes. Every copy's hash
was compared with its temporary original. A directory-local `.gitattributes`
sets `*.txt -text`; source-text captures are deliberately excluded from Git.

Validation of the existing captures established:

- 23 complete metadata bodies: one README, one bundle JSON, two CSVs and 19 READY
  JSON records. JSON decoding rejects duplicate keys, nonstandard constants and
  trailing non-whitespace; CSV parsing checks row widths and complete fields.
- All 23 bodies reconstruct to the remotely measured byte size and SHA-256 after
  accounting for original LF/CRLF endings. The UTF-16LE stdout capture itself is
  not presented as a byte-for-byte copy of each remote file.
- The readiness acquisition had a 131072-byte size guard before cat, not a head
  truncation limit. All 19 files were 539-643 bytes. No MISSING or TOO_LARGE result
  occurred. The four root metadata files were read completely with cat.
- The source excerpt contains every numbered line 1-138 exactly once. Its
  deliberate range boundary is not accidental capture truncation. The root
  listing and declaration locator completed successfully; no independent
  complete-file hash exists for these generated textual outputs.
- Content review and checks found no credential or authentication material:
  no password/passphrase, private-key, authorization/bearer, API-key or token
  patterns, authentication prompts, permission-denied messages, or terminal
  escape sequences. Usernames and historical paths are provenance, not secrets.

## B4 exact sources, paths and source hashes

H-U retains the exact HPC root defined above. W means `E:\johnston_brain` and N
means `E:\johnston_brain\artifacts\GENE_REVIEW_20261004`. W/N are historical
references only; their present existence was not checked.

| Inspected source | Range and evidence class |
| --- | --- |
| H-U and H-U/audit | One successful nonrecursive ls listing; file existence/size metadata. No archives, nested analysis directories or large data opened. |
| H-U/README.txt | Complete, 69 content lines; documentation claims and stated rationale. |
| H-U/BUNDLE_HASHES.json | Complete, lines 1-141, 139 entries; recorded artifact hashes/packaging relationships. |
| H-U/audit/SECTIONS.csv | Complete, header plus 19 rows at lines 1-20; section registry and recorded counts. |
| H-U/audit/GENE_EVIDENCE_INDEX.csv | Complete, header plus 300 gene records; historical inventory, not a new empirical comparison. |
| H-U/sections/<section_id>/READY.json | All 19 exact section IDs in the B4 CSV; complete records, lines 1-13, fields at 2-12. Historical execution/provenance evidence with reuse limitations. |
| H-U/review.py | Declaration locator and lines 1-138; static implemented behavior, not observed execution. |

The [B4 section CSV](SCTRANSFORM_B4_SECTIONS.csv) enumerates every exact readiness
path, its measured byte size/hash and its recorded SCT source path/hash. No
wildcard in this ledger authorizes new reads. Source measurements below were
made during the original B4 acquisition; no HPC rehash occurred during commit.

| H-U-relative source | Remote bytes | Measured source SHA-256 |
| --- | ---: | --- |
| README.txt | 3982 | 2714a689b711e6b4ea57972b005ad4d6ceb8a2432719d312c104166e642b8678 |
| BUNDLE_HASHES.json | 15469 | b138dc9868bbf7ee951d507f7933d90d6728dcb095d3014ccee53f4615f2655f |
| audit/SECTIONS.csv | 13636 | 89579b28336b459f6a0bf5c7f82db2069c83d27072154502b7a1d8853544f513 |
| audit/GENE_EVIDENCE_INDEX.csv | 26464 | e8f6fa2409940fa6783f39b21dfb26e8c04546e1cb8f4de96b123dcc0d4275e3 |
| review.py | 25281 | 8b590e72c4333a1241d5d3fca110cabc1b0cb43da7b5d3b8a8d96788b953173f |

The measured review.py and indexed metadata hashes match their bundle entries;
all 19 measured READY hashes also match. Large NPZ/CSV/RDS objects were neither
opened nor freshly hashed. SCT source and input.npz hashes remain historical
recorded values, distinct from these fresh small-file measurements.

## B4 implemented boundaries and evidence classifications

| ID / class | Evidence and limit |
| --- | --- |
| B4-1 / User decision | Retain log1p(corrected counts) as scientific intent; accept incomplete B4 recovery; no selection/import; preserve source captures outside Git; stop before B5. |
| B4-2 / Implemented behavior | review.py:19-22,70-80 names W/Johnston_MERFISH_Data.h5ad, reads layers/RNA, var/_index, obs/_index, obsm/spatial, sample codes, gen_fine, cluster_coarse and region_labels. Section mask combines sample code and fine label; integer-proximity and section-count assertions follow. No earlier H5AD filtering or raw-data authentication was recovered. |
| B4-3 / Implemented behavior | review.py:82-94 reuses W/sct_work/sct{4,6,14,15,16,17}.csv. Named companions are s{number}_cells.npz (global indices/coordinate assertions), with c15.mtx as the count-comparison fallback. None was opened. |
| B4-4 / Implemented behavior | review.py:95-109 reuses W/region_story/hipp_build_ad/S01_sct.csv with S01_cellmeta.csv; hipp_build_s08/sct.csv with cellmeta.csv; and hipp_build_s12ad/sct.csv with cellmeta.csv. It checks ordered coordinates (direct or swapped), type labels and expected column identifiers. Companions were not opened. |
| B4-5 / Implemented behavior | review.py:110-118 prepares all selected section cells and input genes before glial selection, writes counts.mtx/genes.txt/cells.txt, then conditionally invokes OUT/sct_section.R using the configured R-4.5.3 executable path and logs to sct.log. No SCTransform function call is implemented in review.py itself. R-side filtering/fitting is unknown. |
| B4-6 / Implemented behavior | review.py:121-130 reads the SCT CSV, checks exact expected column order and unique valid gene names, reindexes into original gene order, checks availability over all section cells and nonnegativity of available rows, then selects Mic/AST/OGC. It exports genes x glial cells without another log, centering or scaling. |
| B4-7 / Execution evidence, limited | READY.json:2-12 records section/counts, branch, SCT source/hash, alignment proof, scale and normalization descriptions. review.py:77 skips existing READY; :112-119 skips R for an existing new-branch CSV while still describing it as newly fitted. Records do not prove that a particular preparation invocation executed R or identify executed R source bytes. Assertions can also be disabled. |
| B4-8 / Documentation claim | README.txt:13-20 claims section-specific SCT v2, all cells/300 genes before glial subsetting, no pooling, no Pearson residuals, no second log1p and no SD standardization. It explicitly disclaims cross-section correction-depth harmonization and knowledge of legacy models/reference depths. These claims do not recover the missing recipe. |
| B4-9 / Downstream consumption | All 19 bundle input.npz hashes match B3's recorded source_input_sha256. This links recorded exported artifacts to preparation/GPINIT, not to independently inspected NPZ bytes or actual sampler commands. |
| B4-10 / Unresolved gap | sct_section.R is absent from the root listing and bundle manifest. No actual SCTransform arguments, corrected-count assay/slot/layer, upstream log count, Seurat/sctransform versions, runtime R version or R seed has been recovered. Nine legacy creators remain uninspected. Branch comparability and per-section response certification are not established. |

Output field definitions and the complete raw-source/export graph are in the
[B4 preprocessing increment](SCTRANSFORM_PREPROCESSING.md#b4-accepted-incomplete-increment),
with exact review.py line references. No random operation or seed appears in the
inspected preparation path; that does not determine R-side seeds. The configured
R executable path is not runtime version evidence. Values in READY and README
are not substituted for measured package versions or an executed command record.

### All-section table semantics and checks

SCTRANSFORM_B4_SECTIONS.csv has 19 rows in registry order and 12 columns:
section_id, all_cell_count, glial_count, available_gene_count,
normalization_branch, recorded_sct_source_path, recorded_sct_source_sha256,
readiness_path, readiness_bytes, readiness_sha256, downstream_input_path and
downstream_input_sha256. The last hash is the recorded H-U input.npz hash consumed
by later preparation, not a GPINIT or centered-observation hash.

`new_SCT_recorded` means READY reused_SCT=false (ten rows), not a freshly verified
R execution. `historical_SCT_reused` means reused_SCT=true (nine rows). The field
itself is generated from whether the source path begins with the destination
path (review.py:132). All paths/hashes are exact captured values or explicit
manifest paths. No inferred creator filename is inserted in the CSV.

Every row's all-cell count equals the section registry; glial count equals
n_Mic+n_AST+n_OGC and B3 full_cells. Every row records 300 available genes and
matching measured READY/manifest hashes. All 19 manifest input hashes agree with
B3. Registry section order agrees, including both different S12 identifiers.

README.txt:6-9 describes 72 review candidates; review.py:39-65 derives them from
the S15/S6 panel flags and paper-motivated candidates, but does not use them to
restrict Y. The saved CANDIDATES.csv was indexed, not read. The 300 available genes,
72 review candidates and later 91 modeled genes concern different stages. The
final 91-gene selection rationale is not established by this candidate table.

### Chronology, rationale and contradictions

README.txt:1 dates the review to 2026-10-04. Its scope (:6-9) combines prior S15/S6
panels with paper-motivated candidates. The stated normalization rationale
(:13-20; review.py:3) is to authenticate/reuse prior exports and normalize missing
sections individually. This documents intent to fill coverage, not an empirical
demonstration of improved normalization. No inspected historical user approval
or normalization comparison substantiates superiority.

Nine exports come from sct_work/region_story; ten new-source paths point to N.
The Windows configuration and stored paths are consistent with preparation there
and transfer to HPC, but exact execution and transfer chronology is an inference,
not a recovered run log. The 19 hash links establish later recorded adoption by
the B3 chain, not normalization certification or actual sampler invocation.
No abandonment decision was recovered.

The main provenance discrepancies are the missing required R script; version/model
retention claims without recovered records; and a uniform downstream SCT-v2-log1p
label hiding two upstream branches. The README explicitly documents no depth
harmonization. None of these findings proves a numerical preprocessing error.
Identity checks do not establish normalization semantics. The prior centering
result remains valid within its original mathematical/artifact assumptions.

## B4 acquisition commands

These record the completed B4 reads, not instructions to rerun them. No credentials
or authentication input are recorded. Successful reads used this PowerShell form,
substituting the capture basename and remote body below:

```powershell
$metadataOutput = Join-Path $env:TEMP '<capture-basename>'
$remoteRead = '<remote-body, with embedded single quotes doubled for PowerShell>'
& 'C:\Windows\System32\OpenSSH\ssh.exe' -p 222 -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=yes abussing@login.rci.sc.edu $remoteRead > $metadataOutput
Write-Output "SSH exit code: $LASTEXITCODE"
```

For bsfm-b4-root-listing.txt:

```sh
ls -lan -- /work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1 /work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1/audit
```

For bsfm-b4-root-metadata.txt:

```sh
b=/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1; for f in $b/README.txt $b/BUNDLE_HASHES.json $b/audit/SECTIONS.csv $b/audit/GENE_EVIDENCE_INDEX.csv; do echo BSFM_FILE:$f; wc -c < $f; sha256sum $f; cat $f; echo; done
```

For bsfm-b4-readiness-and-source-index.txt:

```sh
b=/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1; echo BSFM_SOURCE_INDEX:$b/review.py; wc -c < $b/review.py; sha256sum $b/review.py; rg -n '^(def |class |[A-Z_][A-Z_0-9]* *=)' $b/review.py; for s in S00__Trem2_5xFAD4 S01__5xFAD4 S02__Trem2_4 S03__Trem2_5xFAD3 S04__WT3 S05__Trem2_3 S06__5xFAD3 S07__Trem2_5xFAD5 S08__5xFAD5 S09__Trem2_5 S10__WT5 S11__Trem2_5xFAD1 S12__Trem2_1 S12__Trem2_5xFAD2 S13__Trem2_2 S14__WT1 S15__5xFAD1 S16__WT2 S17__5xFAD2; do f=$b/sections/$s/READY.json; echo BSFM_FILE:$f; if test -f $f; then n=$(wc -c < $f); echo $n; if test $n -le 131072; then sha256sum $f; cat $f; else echo TOO_LARGE; fi; else echo MISSING; fi; echo; done
```

rg was unavailable; that locator failed, but the source size/hash and all readiness
reads succeeded. Consequently this capture contains no source-code declarations.
The locator was repeated using grep, producing external capture D:

```sh
f=/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1/review.py; grep -nE '^(def |class |[A-Z_][A-Z_0-9]* *=)' $f
```

For external source excerpt X:

```sh
head -n 138 /work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1/review.py | nl -ba
```

An initial listing connection returned no captured output and did not record the
SSH exit code; it supplies no evidence. The successful retry recorded exit zero.
An earlier locator/readiness command used double quotes around the regex, which
were stripped during native argument passing; remote shell parsing failed before
file reads. The corrected command above supplied the retained evidence. All
successful acquisition bodies were read-only shell utilities, not project code.

Local preservation used byte copies and SHA-256 comparisons; Python standard
library JSON/CSV parsing reconstructed remote metadata bytes from the stdout
captures and checked counts/hashes against the B3 CSV. These checks operated only
on existing small local evidence and did not execute any historical implementation.

## B5 proposed boundary, not begun

The exact missing reference is H-U/sct_section.R (review.py:118). Its historical
Windows location is inferred as `E:\johnston_brain\artifacts\GENE_REVIEW_20261004\sct_section.R`
from OUT and the recorded new-export destinations. Its existence was not checked.
An approved continuation should locate that small source and directly referenced
helpers, then small sct.log and environment/version records for the ten new sections.
Names of additional version records are not yet known; no RDS/model is to be
opened as a substitute for provenance.

Creator filenames for the nine reused exports are not recovered. A separate
bounded nonrecursive discovery would be needed in these exact historical roots:

- `E:\johnston_brain\sct_work`
- `E:\johnston_brain\region_story\hipp_build_ad`
- `E:\johnston_brain\region_story\hipp_build_s08`
- `E:\johnston_brain\region_story\hipp_build_s12ad`

No such discovery occurred. Exact source CSV paths are recorded in the B4 table,
but no large CSV, NPZ, H5AD, RDS, archive or fitted model was inspected or hashed.
Both normalization branches must be understood before declaring this capability
recovered. B5 requires review/approval before expansion; this checkpoint selects
no implementation and certifies neither expression scale nor branch comparability.

## B5/B5b capture preservation and validation

User decision U6: accept B5/B5b as the endpoint of bounded historical
normalization-source discovery; preserve negative and duplicate evidence, update
capability status and commit before any replacement design. No broader search or
replacement implementation was authorized. U6 explicitly authorized hashing and
listing the two named large archives in B5b; no large archive was rehashed while
preparing this checkpoint.

Seven existing captures were copied byte-for-byte from
`C:\Users\Data Viz\AppData\Local\Temp\` into
[evidence/sctransform_b5/](evidence/sctransform_b5/). Their combined size is
**946055 bytes**, below 2 MiB (2097152 bytes). Original encodings/BOMs and line
endings are retained. Directory-local `.gitattributes` disables text conversion
for both TXT and JSON captures. The SHA-256 values below identify these captures,
not the remote archives or individual members described within them.

| Original/preserved basename | Bytes | Capture SHA-256 |
| --- | ---: | --- |
| bsfm-b5-root-discovery.txt | 35208 | 3bc90b996f9fc0acfcbabad95d0276e721a04bee8265466c3aae1a72293ef746 |
| bsfm-b5-bounded-filename-search.txt | 1206 | 7686c380abfef1894276ae527122af2546522263829be836e16bb4f376598a01 |
| bsfm-b5-associated-index-search.txt | 1260 | d19653c4e6ba830d1c6fa4dc1c0dbb32515b50a1ce6273c519992008e68e989a |
| bsfm-b5b-archive-listings.txt | 812156 | fc3fbd3e08db5c9a1ea95660b2e5d657f48de8dfb068bb5318c68ae7c269e4b5 |
| bsfm-b5b-cpu-provenance-stream.txt | 85252 | 616f861c035e103247e24cac1cb6dc70b8f9f2a9ce160ab8f638203dd2b8addc |
| bsfm-b5b-member-inventory.json | 9750 | 25fd98c0114738e52725c9a154a5f31dc7be6181a1a9c5823b473bef2616cc68 |
| bsfm-b5b-acquisition-commands.json | 1223 | fde26c27bba49566a4a538270dd7ee99273bbc4cfafa52cb480e15c05b343a8e |

These contain discovery/metadata results, archive listings, acquisition commands
and duplicate provenance, not legacy implementation bodies. The base64 stream
contains only README.txt, BUNDLE_HASHES.json and 19 READY.json files. It permits
exact reconstruction of those 30888 member bytes without duplicating them in Git.
The inventory's LocalPath fields preserve original temporary decoded-member paths;
the durable member evidence is the committed stream plus per-member size/hash,
not continued availability of those temporary decoded files.

Validation before preservation and consistency checks established:

- All 393 root inventory lines parse as type/size/name: 267 directories and 126 files.
- The bounded search capture has both completion markers at exit zero; its five
  metadata matches parse completely. No source match occurred between the source
  search markers. Depth/pruning/time limits remain part of the negative claim.
- The associated manifest search returned grep exit 1 (no match), not a read-error
  status. Its seven-member archive listing completed at exit zero.
- Both large-archive listings contain completion markers at exit zero. All 140
  and 4183 member lines parse into mode, owner, size, timestamp and path, with no
  unexplained member lines. No output truncation cap was applied to these captures.
- All 21 selected-member streams have exit zero; base64 decodes completely. Every
  decoded size matches both the archive listing and the inventory; every fresh
  decoded-byte SHA-256 matches the inventory and B4's corresponding source hash.
  All 20 JSON members parse completely; the remaining member is the full README.
- The CPU archive's path set is exactly the manifest's 139 entries plus
  BUNDLE_HASHES.json. All 19 READY records retain the B4 identities/counts/paths
  and the ten-new/nine-reused split. The two capture JSON records (inventory and
  acquisition commands) parse completely as well.
- All seven copied capture hashes equal their originals. Content review and
  pattern checks cover both the captures and decoded base64 bodies: no credentials,
  private keys, authorization/bearer material, API/access/refresh/client-secret
  tokens, authentication prompts or terminal escapes were found. Historical
  usernames/paths are retained as provenance, not secrets.

No HPC connection, new discovery, historical code execution or repository source
import was used to preserve this checkpoint. Validation used local PowerShell/.NET
reading, parsing, hashing and comparison of already captured evidence. It did not
run R, Python or any historical implementation.

## B5 exact search boundaries and results

H-S denotes `/work/abussing/arka_trying_gpu_again`; H-U is its
`gene_review19_20261004_v1` child. W and N retain their B4 meanings.
The [machine-readable search ledger](SCTRANSFORM_B5_SEARCH_LEDGER.csv) has 18 rows
and seven columns: search_id, source_location, search_boundary, evidence_type,
result, remaining_gap and evidence_reference. It separates inaccessible paths,
bounded negative searches, filename inventories and measured duplicate provenance.
The final five rows record the later drive-attachment availability change.

The five exact local checks were:

1. `E:\johnston_brain\artifacts\GENE_REVIEW_20261004\sct_section.R`
2. `E:\johnston_brain\sct_work`
3. `E:\johnston_brain\region_story\hipp_build_ad`
4. `E:\johnston_brain\region_story\hipp_build_s08`
5. `E:\johnston_brain\region_story\hipp_build_s12ad`

Test-Path -LiteralPath returned false for each; Get-PSDrive -PSProvider FileSystem
reported only C:. No local listing occurred because the locations were inaccessible.
These observations were returned in the B5 conversation tool output, not a separate
preserved local-check stdout capture. The ledger records that limitation rather
than inventing a raw capture. They establish unavailable E: access, not deletion.

| Search | Boundary and result | Evidence class / limitation |
| --- | --- | --- |
| H-S root | find mindepth 1 / maxdepth 1: 393 entries. | Filename inventory only; no file contents. |
| H-S normalization R names | maxdepth 3, timeout 45s; case-insensitive *sct*.r, *sctransform*.r, *seurat*.r, *normaliz*.r. Prune env, gpu_sparse_backend_env, .git, .venv, __pycache__, plots*, outputs, errors, datasets*. No matches; exit 0. | Bounded negative search; not exhaustive for deeper/excluded paths or differently named scripts. No symlink following requested. |
| H-U associated records | maxdepth 4, timeout 30s; names matching session, version, environment, manifest, hash, sct.log, .r, .tar.gz or .zip patterns. Five matches; exit 0. | No R/session/version/sct.log match within this boundary. Contents of data were not searched. |
| H-U/all300_gp_extension_v1/MANIFEST.json | 206099 bytes; SHA-256 0e0dfeb6c573665505f145059e367043dbb30b3137153b9c44419d544179deb7. Targeted reference grep returned no match (exit 1). | Small metadata-reference search, not implementation inspection. |
| H-U/all300_gp_extension_v1.tar.gz | 106905 bytes from filename discovery; name listing only, timeout 30s, seven members, exit 0. | No R/version-record filename. No archive hash or member contents inspected in this step. |

The five H-U matches were BUNDLE_HASHES.json (15469 bytes), the extension manifest
(206099), the extension archive (106905), gene_review19_cpu_bundle.tar.gz (43252255)
and gene_review_results_20261005.tar.gz (102728274). The two larger archives were
initially left unopened, then explicitly authorized for B5b below. The extension
archive contained extension.py, WORKLIST.csv, submit_extension.sh, submit_smoke.sh,
submit_report.sh, launch.sh and MANIFEST.json under all300_gp_extension_v1/.
Their implementation/data contents were not inspected.

## B5b archive identities and member evidence

These hashes were measured on the two exact remote archives during B5b. They are
distinct from capture hashes and from historically recorded scientific hashes.

| Exact H-U-relative archive | Bytes | Members | Measured SHA-256 |
| --- | ---: | ---: | --- |
| gene_review19_cpu_bundle.tar.gz | 43252255 | 140 | cb1a79daa051083350c1036fb5bec4f327cb8cca8f4a7e6666fb261c3c117732 |
| gene_review_results_20261005.tar.gz | 102728274 | 4183 | b286e99695cf1f24fd2da4490017dce16ebe98ab83cd45b7a50a30a89247b903 |

The complete inventories, including each member path and uncompressed size, are
in [bsfm-b5b-archive-listings.txt](evidence/sctransform_b5/bsfm-b5b-archive-listings.txt).
Neither lists sct_section.R, any .R/.r member, an SCT/Seurat/normalization-named
source, session/version/environment/package-version member, sct.log, sct_work,
region_story, hipp_build_* or the reused SCT CSV names. The nine exact source
paths being sought remain in the B4 section table; their unique basenames are
S01_sct.csv, sct4.csv, sct6.csv, sct.csv, sct14.csv, sct15.csv, sct16.csv and sct17.csv
(sct.csv occurs in two distinct parent directories).

| Archive inventory category | CPU bundle | Results archive |
| --- | ---: | ---: |
| Directories | 0 | 20 |
| Python sources | 3 | 0 |
| Shell source | 1 | 0 |
| CSV members | 3 | 0 |
| TXT members | 1 | 0 |
| JSON members | 20 | 19 |
| NPZ artifacts | 112 | 4104 |
| OUT/ERR logs | 0 | 40 |

CPU source names are the known review.py, test_review.py, verify_bundle.py and
submit_cpu.sh; they were not streamed or newly inspected as implementation in B5b.
The results JSONs are section GP_RUN_CONFIG.json records. Its logs range from 0
to 17205 bytes (296577 bytes total). Their GP-fitting role did not establish
relevance to the missing normalization source; neither configurations nor logs
were opened. No log was in the 512 KiB-2 MiB approval band. Absence of named
normalization records does not prove absence of every possible detail hidden
inside uninspected GP logs/configurations.

Only these 21 exact CPU-bundle provenance members were streamed:

- README.txt: 3982 bytes, SHA-256 2714a689b711e6b4ea57972b005ad4d6ceb8a2432719d312c104166e642b8678.
- BUNDLE_HASHES.json: 15469 bytes, SHA-256 b138dc9868bbf7ee951d507f7933d90d6728dcb095d3014ccee53f4615f2655f.
- sections/<section_id>/READY.json for all 19 exact B4 section IDs: 11437 bytes
  total, 539-643 bytes each. Every individual path/size/hash is preserved in
  [bsfm-b5b-member-inventory.json](evidence/sctransform_b5/bsfm-b5b-member-inventory.json)
  and agrees with the B4 section table's readiness hash.

All 21 are individually below 512 KiB; largest is 15469 bytes. Their exact bytes
are recoverable from the base64 member stream. Full README inspection and JSON
parsing found identical B4 content. README:13-20 repeats reuse/new-SCT claims and
no correction-depth harmonization. READY:6-11 repeats branch/source/hash/alignment
and scale descriptions. These are duplicates, not independent recipe verification.
No source code, expression CSV, NPZ, H5AD, RDS, fitted model or plot member was
extracted or inspected. Streaming wrote only local temporary evidence, never HPC
files. The tar list/stream utilities do not execute member code.

## B5/B5b acquisition commands

These record prior acquisition only. No command below was rerun to prepare this
checkpoint. Local checks used Test-Path -LiteralPath on the five exact Windows
paths above, and Get-PSDrive -PSProvider FileSystem. Conditional nonrecursive
listings were not reached because all paths were inaccessible.

SSH used this form with each exact remote body and capture basename:

```powershell
$metadataOutput = Join-Path $env:TEMP '<capture-basename>'
$remoteRead = '<remote-body, with embedded single quotes doubled for PowerShell>'
& 'C:\Windows\System32\OpenSSH\ssh.exe' -p 222 -o ConnectTimeout=20 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -o StrictHostKeyChecking=yes abussing@login.rci.sc.edu $remoteRead > $metadataOutput
Write-Output "SSH exit code: $LASTEXITCODE"
```

For bsfm-b5-root-discovery.txt:

```sh
find /work/abussing/arka_trying_gpu_again -mindepth 1 -maxdepth 1 -printf '%y\t%s\t%f\n'
```

For bsfm-b5-bounded-filename-search.txt:

```sh
b=/work/abussing/arka_trying_gpu_again; echo B5_SOURCE_NAMES; timeout 45s find $b -maxdepth 3 -type d \( -name env -o -name gpu_sparse_backend_env -o -name .git -o -name .venv -o -name __pycache__ -o -name 'plots*' -o -name outputs -o -name errors -o -name 'datasets*' \) -prune -o -type f \( -iname '*sct*.r' -o -iname '*sctransform*.r' -o -iname '*seurat*.r' -o -iname '*normaliz*.r' \) -printf '%s\t%p\n'; echo SOURCE_SEARCH_EXIT:$?; echo B5_REVIEW_METADATA_NAMES; timeout 30s find $b/gene_review19_20261004_v1 -maxdepth 4 -type f \( -iname '*session*' -o -iname '*version*' -o -iname '*environment*' -o -iname '*manifest*' -o -iname '*hash*' -o -iname 'sct.log' -o -iname '*.r' -o -iname '*.tar.gz' -o -iname '*.zip' \) -printf '%s\t%p\n'; echo METADATA_SEARCH_EXIT:$?
```

For bsfm-b5-associated-index-search.txt, the submitted remote body was:

```sh
b=/work/abussing/arka_trying_gpu_again/gene_review19_20261004_v1; f=$b/all300_gp_extension_v1/MANIFEST.json; echo B5_MANIFEST:$f; wc -c < $f; sha256sum $f; grep -nEi 'sct_section[.]r|sctransform|seurat|session|version|sct[0-9]*[.]csv|sct[.]log|sct_work|hipp_build|[.]r"' $f; echo MANIFEST_MATCH_EXIT:$?; echo B5_SMALL_ARCHIVE_LISTING; timeout 30s tar -tzf $b/all300_gp_extension_v1.tar.gz; echo ARCHIVE_LIST_EXIT:$?
```

The submitted grep expression contains a final double-quote character; Windows
native argument handling may strip it. No recipe finding relies on that optional
generic suffix: the explicit sct_section/SCT/Seurat/version terms were separate
alternatives, and the recorded grep outcome was no match, not a syntax error.

The exact B5b listing and selected-member stream commands, including the literal
21-member allowlist, are preserved in
[bsfm-b5b-acquisition-commands.json](evidence/sctransform_b5/bsfm-b5b-acquisition-commands.json).
The listing used stat -c '%s', sha256sum and tar --numeric-owner --full-time -tvzf
on only the two named archives. The stream used tar -xOzf on each exact member,
base64 -w0 for byte preservation, and pipefail plus a per-member status marker.
Authentication input was never included in captures or command documentation.

## Accepted conclusion and next decision boundary

The historical exporter and downstream artifact chain are recovered at the level
of inspected behavior and recorded metadata links. Actual sampler invocation
remains uncertified. The normalization recipe cannot be certified from accessible
evidence; the ten-new/nine-reused branches are not proven comparable. Correction
depths were explicitly not harmonized. Historical log1p(corrected counts)
construction remains a claim, while log1p(corrected counts) is the recovered
scientific intent.

This does not prove the historical procedures were wrong or permanently
unrecoverable. No newly recovered execution record, user approval, empirical
normalization comparison or creator implementation closes either branch's gap.
No historical implementation is selected. The capability statuses are: scientific
response intent recovered; downstream exporter/handoff recovered within the stated
evidence limits; historical normalization implementation unresolved; uniform
cross-section comparability unestablished; replacement design not yet approved.

The bounded HPC search is closed by user decision, not by a claim that every possible
backup or HPC file was exhausted. A later decision may consider a known historical
E: backup and a uniform version-pinned design after settling scientific choices
and locating authoritative raw counts. No such search, design or implementation
is performed or approved by this checkpoint.

## Local drive attached during checkpoint preparation

After the B5/B5b report and while preparing this commit, the user connected the
historical drive. Get-PSDrive reported C: and D:. Test-Path -LiteralPath succeeded
for all five paths below; the corresponding E: checks still returned false:

- `D:\johnston_brain\artifacts\GENE_REVIEW_20261004\sct_section.R`
- `D:\johnston_brain\sct_work`
- `D:\johnston_brain\region_story\hipp_build_ad`
- `D:\johnston_brain\region_story\hipp_build_s08`
- `D:\johnston_brain\region_story\hipp_build_s12ad`

These are local access observations, not source inspection, execution or scientific
verification. No directory contents or implementation files were opened. This
availability change is preserved separately in
[bsfm-b5-local-drive-attached.json](evidence/sctransform_b5/bsfm-b5-local-drive-attached.json).
The initial unavailable E: observations remain historical facts; they no longer
justify assuming that the known local evidence cannot be accessed. Targeted local
recovery is now possible, while historical normalization remains uncertified and
replacement design remains unapproved. No broader HPC excavation was performed.

The new availability capture is 2151 bytes, SHA-256
`31da36b18aa467051cda3e6f67f87bf2365a43aeaf2a196c06c0c37b5dc65386`.
It parses completely and contains only context, drive roots and ten path/access
results. Together with the seven original captures, the eight preserved files
total 948206 bytes, still below 2 MiB. Its Git copy matches the local original
byte-for-byte and contains no credential or authentication material.
