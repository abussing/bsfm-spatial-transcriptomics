# SCTransform evidence ledger through Stage B3

Checkpoint date: 2026-10-30. Scope: B1 metadata/provenance, B2 six-file source
inspection, and the accepted B3 local handoff/HPC metadata increment. The B1/B2
checkpoint remains available at `d2e7e5ea9db420fe2910cd54ac1e33040a0726db`.
Earlier-stage sections below retain their stage-specific limits; the appended B3
ledger records subsequent evidence. No implementation has been selected.
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
H-U was referenced by returned contracts but was not accessed.

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
