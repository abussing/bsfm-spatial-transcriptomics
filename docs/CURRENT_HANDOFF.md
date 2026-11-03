# Current BSFM handoff

Updated 2026-11-03 after completed shutdown preservation and artifact transfer.
This supersedes the earlier handoff's pending-transfer statements; older audits
remain evidence of their original inspections.

## Accepted baseline and unreviewed work

Accepted scientific/preparation main baseline:
`9c584353e74043e323ca327ff1764f9d094980d5`
(`docs: register canonical S10 full-cell preparation artifacts`). The subsequent
main commit containing this handoff changes documentation only.

Read [AGENTS.md](../AGENTS.md), [CAPABILITIES.md](../CAPABILITIES.md), the
[sampler architecture](decisions/BSFM_SAMPLER_ARCHITECTURE.md),
[Layer 8](sampler/LAYER8.md), [Layer 9A design](sampler/LAYER9A_DESIGN.md), and
[accepted S10 full-cell preparation](initialization/S10_FULLCELL_PREPARATION.md).
Layers 1-8 are accepted. Layer 9 and leave-out prediction are **not accepted**.
The Layer-9A design's original preparation gaps are resolved only to the extent
established by the separate accepted S10 v2 receipt; it is not implementation
validation.

The interrupted Layer-9 draft is preserved separately on GitHub:

- Branch: `wip/layer9-orchestration-20261103`.
- Commit: `a87532ec30d6daacada3245e2cbeb105da4435ce`.
- Status: **UNREVIEWED, INCOMPLETE, NONCANONICAL. Do not run on scientific data.**
- Thirteen committed files: six draft source modules, three test/support files,
  and `docs/wip/layer9_20261103/{STATUS.md,focused-partial.log,inventory.csv,work.patch}`.
- The inventory authenticates twelve files, excluding itself to avoid circularity;
  all twelve byte counts/hashes were verified against the pushed Git blobs.
- No complete Layer-9 test pass or synthetic continuation result exists. Both
  exploratory test process trees were stopped. The retained partial log predates
  the final snapshot of tests and does not validate that snapshot.
- All accepted Layers 1-8 numerical code, fixtures and environments remain unchanged.

The draft includes initialization/adaptation, genesis, transaction publication
and repair, storage, and authenticated NPZ-only inputs. Review it against the
approved design before further development. Do not merge it as accepted code.

## Canonical artifacts: verified HPC computational mirror

HPC: `abussing@login.rci.sc.edu`, SSH port `222`, interactive authentication/Duo.
Destination:

```text
/work/abussing/bsfm-consolidation/canonical-artifacts-20261103
```

**Complete and independently verified at 2026-11-03 06:40:32 UTC:**
187 payload files, **6,943,739,779 bytes**. No incomplete or mismatched payload
remains in the transfer receipt. Desktop originals remain authoritative; this is
a replaceable HPC computational mirror, not archival storage. Scratch retention
is still a durability limitation, not a blocker to this authorized copy.

| Destination-relative component | Files | Bytes | Result |
| --- | ---: | ---: | --- |
| `s10-preparation-v2/` | 24 | 4,899,499 | Verified complete |
| `s10-mesh/` | 12 | 8,073,940 | Verified complete |
| `sct-v2/` | 137 | 1,446,987,796 | Verified complete |
| `raw/` | 1 | 5,483,600,151 | Verified complete |
| `receipts/external/` | 1 | 19,720 | Verified complete |
| `receipts/sct-v2/` | 4 | 74,765 | Verified complete |
| `receipts/s10-preparation-v2/` | 4 | 75,133 | Verified complete |
| `receipts/s10-mesh/` | 4 | 8,775 | Verified complete |

Control inventories/receipts below are additional to the 187 payload files.
Every destination payload was SHA-256/size checked independently on HPC before
and after promotion from `.incomplete`, then checked again in a final complete
inventory pass. Already transferred files and partial prefixes were authenticated
before reuse. A post-transfer rehash of all 187 desktop sources also passed.
No desktop source artifact was changed, and no installed Windows environment
was transferred.

The initial sessions stopped during verifier setup/verification and retained
partial files. Repeated SSH command channels caused repeated approvals; the
successful helper used one persistent remote verifier and one SFTP channel.
The final receipt includes authenticated files reused from those partial copies;
this is transport resumption, not scientific regeneration or reuse of rejected
scientific artifacts. Credentials were not written to scripts, repository files,
environment variables or transfer logs. No scientific HPC job was submitted.

### Receipt and inventory identities

All four files are at the HPC destination above. Byte-identical local copies:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_RECOVERY_EVIDENCE\portability_20261103
```

| Control file | Bytes | SHA-256 |
| --- | ---: | --- |
| `source-inventory.json` | 71,037 | `8d5861b3ac76b4e4eaea5fd8d979cb360b3d425530d0b4faadb79a65b7f51a79` |
| `source-inventory.csv` | 46,075 | `b30c0a8562be6871e6edfb81c8e525310c17ea3346f2b228afa1fd8e30b30752` |
| `transfer-receipt.json` | 45,963 | `5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60` |
| `destination-verification.json` | 36,311 | `8254cd7d7a4e96665a667d6a226a636076944f6161646d7ea8ea62984e69ba65` |

The inventory preserves exact original machine-local paths and their mapping to
HPC-relative paths. Internal Windows provenance strings were copied unchanged;
they are not Linux runtime paths. Do not rewrite immutable scientific contracts
to pretend artifacts were generated on HPC. Resolve actual artifact paths
explicitly while retaining their authenticated identities.

Required payload identities:

- `s10-mesh/sampler-facing.npz`: 7,195,273 bytes;
  `69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0`.
- `sct-v2/run-manifest.json`:
  `03b83d93891080f15b6a85684e2cb5de8d9a9b7cdf72f8c25dd8103403e1e06f`.
- `raw/Johnston_MERFISH_Data.h5ad`: 5,483,600,151 bytes;
  `d6876020cfdb5cb2fdeb848550e8334cfc2684b6ce6f7755b862cac567f06a38`.

The S10 v2 package contains the exact 9,422-cell canonical response/mesh join,
prepared model input, two deterministic GPINIT fits and independent readbacks.
Its clean generating commit remains
`679a7432430464ba0031f9762b77e48f50946964`; registration and transfer do not
change the producer. K=20, nfit=250 and seed=2026102610 remain mechanical gate
settings, not production choices. Historical 4,712-cell artifacts are not
substitutes. See the [v2 receipt](initialization/audits/S10_fullcell_v2_20261103/receipt.json).

## Environment and scientific limits

Existing HPC sampler CPU environment:

```text
/work/abussing/bsfm-consolidation/environments/sampler-cpu-py311
```

The [passing Linux CPU audit](environment/HPC_SAME_ENVIRONMENT_VALIDATION.md)
records job 22012334: 75 tests and seven same-environment historical/port
comparisons. This is its bounded historical validation scope, not validation
of later Windows-only sampler layers, the WIP runner, or a GPU production fit.
Use platform-specific locks and receipts; do not copy Windows virtualenvs or
silently substitute dependency versions.

**Canonical Linux fmesher remains incomplete.** Job 22012400 timed out
(exit `1:0`, elapsed `02:00:09`, batch MaxRSS `902232K`); R and 20 packages
completed, with the retained log stopping in s2. Fresh package/version/isolation
validation and canonical Linux mesh reproduction were not reached. Preserve the
partial prefix. See the [terminal record](environment/HPC_R_MESH_BUILD_22012400.json).
The accepted Windows mesh and the transferred canonical mesh artifacts remain
valid within their recorded scope; this transfer does not reproduce them on Linux.

Full-data SCT at depth 124 is **ineligible for primary holdout scoring**.
The copied S10 preparation is full-data preparation. Future primary leave-out
experiments require approved training-only preprocessing/fitting/depth/centering
populations and an explicit scoring policy. Reuse the approved fixed-design mesh
for chunk holdouts; do not silently substitute historical responses or rebuild
geometry after removing observations. No leave-out workflow, scientific fit,
production K, chain count, or run lengths were selected by this task.

## Exact resume instructions on another computer

1. Clone accepted main and inspect the WIP without mixing it into main:

   ```sh
   git clone https://github.com/abussing/bsfm-spatial-transcriptomics.git
   cd bsfm-spatial-transcriptomics
   git fetch origin
   git status --short --branch
   git rev-parse HEAD origin/main
   git show origin/wip/layer9-orchestration-20261103:docs/wip/layer9_20261103/STATUS.md
   git worktree add --detach ../bsfm-layer9-review origin/wip/layer9-orchestration-20261103
   ```

   Verify the WIP commit equals `a87532ec30d6daacada3245e2cbeb105da4435ce`.
   Read its status, inventory and patch before editing. Main must stay clean.

2. Authenticate once to HPC, then run the following read-only integrity check
   inside that shell. This hashes payload bytes; it does not execute a sampler:

   ```sh
   ssh -p 222 abussing@login.rci.sc.edu
   /work/abussing/bsfm-consolidation/environments/sampler-cpu-py311/bin/python - <<'PY'
   import hashlib, json
   from pathlib import Path
   root = Path('/work/abussing/bsfm-consolidation/canonical-artifacts-20261103')
   def sha(p):
       h = hashlib.sha256()
       with p.open('rb') as f:
           for chunk in iter(lambda: f.read(1048576), b''):
               h.update(chunk)
       return h.hexdigest()
   assert sha(root/'source-inventory.json') == '8d5861b3ac76b4e4eaea5fd8d979cb360b3d425530d0b4faadb79a65b7f51a79'
   assert sha(root/'transfer-receipt.json') == '5ed5813756a19c73f672c6873b6f41093521ea1dd4a46d8a075ff18d13bb4f60'
   assert sha(root/'destination-verification.json') == '8254cd7d7a4e96665a667d6a226a636076944f6161646d7ea8ea62984e69ba65'
   inv = json.loads((root/'source-inventory.json').read_text())
   receipt = json.loads((root/'transfer-receipt.json').read_text())
   assert receipt['status'] == 'complete_verified'
   assert len(inv['files']) == len(receipt['files']) == 187
   for row in inv['files']:
       p = root / row['relative_path']
       assert p.stat().st_size == row['bytes'], str(p)
       assert sha(p) == row['sha256'], str(p)
   assert sum(r['bytes'] for r in inv['files']) == receipt['total_verified_bytes'] == 6943739779
   print('PASS: 187 payloads, 6,943,739,779 bytes')
   PY
   ```

   If downloading to another computer, preserve the relative layout and repeat
   the inventory check with `root` pointing at that local mirror. Never infer
   integrity from a successful copy command or directory existence.

3. Resume **review and bounded implementation**, not a scientific run. In the
   separate WIP worktree, authenticate the twelve inventory entries, inspect
   the draft against Layer 9A, finish initialization/RNG equivalence, genesis,
   transaction crash/recovery and non-replay tests, and run the complete
   sampler/provenance and eight canonical mesh suites in their accepted
   environments. The existing draft's partial log is not a pass. No package
   change, tolerance relaxation or automatic WIP promotion is authorized here.

4. Preserve the approved NPZ/contract runtime boundary, target acceptance 0.9,
   immutable run identity, separate genesis, per-sweep atomic transaction,
   repairable projections, exact same-run resume and deferred readaptation.
   Timing remains outside authoritative scientific records. Do not reopen
   preparation, GPINIT or Layers 1-8 to evade a draft failure.

5. After Layer-9 review/acceptance, separately specify and seek approval for
   the S10 leave-out-chunk pilot: training-only preprocessing and scoring,
   held-out identities, fixed geometry, explicit run parameters and platform
   validation. The current full-data artifacts support mechanical integration,
   not an honest primary holdout score. Any HPC job requires a committed run
   specification and explicit approval under AGENTS.md.

No transfer remains to resume. Operational helper scripts and interruption
records remain in the local evidence directory above; no further scientific
implementation was added during shutdown preservation. Large payloads,
checkpoints, environments and logs remain outside Git.
