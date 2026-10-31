# Canonical single-section modeling response

Status: single-section implementation, independent validation, S00 equivalence
and six-file portability accepted by explicit user approval. The subsequent
shared-root/committed-provenance orchestration implementation and tests are
accepted. Canonical full-data v2 production subsequently passed for all 19
sections; see the [production receipt](audits/20261031_production_v2/README.md)
and [production orchestration](PRODUCTION_ORCHESTRATION.md). Full-data artifacts
are not eligible for primary holdout scoring.
Execution baseline: `51441c885ecf5f4ac19d10a8b399d7d1ade46e1f`.
The user authorized the single-section runner, independent validator, refactor
tests and one fresh S00 bundle before commit. Other real sections, holdout
preprocessing, meshes, GP initialization and HPC execution are outside this gate.

The [handoff decision](../decisions/MODELING_RESPONSE_HANDOFF.md) and frozen panel,
bundle and final-manifest schemas remain unchanged. The new
[run configuration](../../config/preprocessing/single-section-run.json) supplies
mechanical storage settings and explicit float64 tolerances. Configuration
overrides must match the canonical configuration bytes; registered source,
panel, section, schema and environment identities are checked before fitting.

## Shared core and interfaces

`src/bsfm/preprocessing/sct_core.R` contains the sole authoritative `fit_correct`
implementation, extracted from the accepted validation runner without changing
its algorithm. Both validation and production call the same R validation driver
and core. Seeds, v2, glmGamPoi_offset, all-cell fitting, all-300-gene input,
correct_counts and exactly one log1p are preserved. No fallback is accepted.
The existing raw preflight remains separate.

Run from the repository checkout using the existing Python environment with
NumPy, h5py, psutil and jsonschema; no dependency is installed by these commands.
The `production` optional dependency group declares the additional packages.

```powershell
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m bsfm.preprocessing.response_run `
  --section '<exact registered section ID>' `
  --raw-source '<authenticated H5AD path>' `
  --environment '<accepted isolated R environment>' `
  --config config/preprocessing/single-section-run.json `
  --destination-root '<fresh external directory>'
```

The interface is general; only the earlier bounded gate executed real S00.
Production requires a clean committed checkout; this orchestration gate runs
only synthetic tests. It rejects unknown
sections and inconsistent configuration before fitting. The authenticated source
has no excluded cells, so v1 requires exact agreement with the accepted eligible
population and rejects any changed count/metadata/source rather than introducing
new eligibility rules. Standalone use rehashes the source in full as opaque bytes; a launcher may
supply its active process-local start authentication. Expression extraction is
bounded and restricted to the selected section. IDs, raw rows,
animal labels and coordinates come from the canonical source/registries.

The bundle contains exactly response.h5, fit.rds, execution.json, session.txt,
validation.json and manifest.json. It preserves all-cell counts and log1p values,
the 91-gene selected response, once-centered Y, means, group sizes and identities.
Coordinates remain unchanged, source_native, in center_y/center_x order. The
physical HDF5 layout uses lossless gzip level 4 and numeric shuffle; actual chunk
shapes/filter settings are recorded per dataset. All payloads are float64/int64
little-endian or UTF-8 as specified. Array hashes use logical C order, independent
of compression and RDS serialization. No legacy code was imported.

## Independent validation

```powershell
python -m bsfm.preprocessing.response_validate `
  --bundle '<final directory named by section ID>' `
  --raw-source '<authenticated H5AD path>' `
  --environment '<accepted isolated R environment>' `
  --config config/preprocessing/single-section-run.json `
  --work-dir '<fresh external validation evidence directory>'
```

The validator does not import the bundle writer. It reopens HDF5, metadata and
fit.rds, independently reauthenticates the source, reconstructs identities and
selection from raw metadata, and checks schemas, all hashes, physical storage,
axes, mappings, coordinates, fitting cells, method, gene availability and group
membership. A separate R process reads the saved fit and raw input and calls
correct_counts without refitting; the validator compares the resulting count
and log1p payloads exactly with HDF5. This also verifies the effective arguments
and unchanged R semantic hashes. Recorrection is validation, not another SCT fit.

Exact log1p equality uses the pinned R math implementation, which generated the
accepted response. NumPy's log1p is not presumed bitwise equivalent to that
implementation. Exact equality is required for axes, selection, coordinates,
corrected values, log1p readback and `Y = L - recorded_means`. Independent mean
reduction and arithmetic reconstruction use these explicit limits:

| Check | Absolute tolerance | Relative tolerance |
| --- | ---: | ---: |
| Centered group-mean residual | 1e-12 | 0 |
| Reconstruction of L from Y + means | 1e-15 | 1e-14 |

Mean recomputation now uses the accepted [forward-error check](MEAN_ROUNDOFF_VALIDATION.md)
against math.fsum/n, with a group-size/magnitude-dependent allowance and frozen
safety factor two. Every discrepancy and bound is retained. The generic
means_atol/means_rtol check is removed; writer output is unchanged.

Both reconstruction/residual maxima and tolerances are retained. No tolerance changes count identity,
allows an additional transform, or changes the scientific centering equation.
Stack-imbalance text in any normalization/readback log or recorded warning is
fatal; no warning is suppressed and no package version changes. Exact closed
normalization and transport-readback log bytes are embedded in execution.json
as base64. Each log records its encoding, byte count, SHA-256 and decoded warning
scan. The independent pre-promotion readback log is embedded the same way in
validation.json. Validation decodes and authenticates the bytes, recomputes the
scan and rejects stack-imbalance warnings. It never opens an original log path.
External command/output/log paths are non-authoritative provenance strings.

Manifest JSON Schema is only a structural check. The closed-file numerical and
identity checks are also required. Final validation repeats them and compares
the recorded validation report against independently measured results.

## Identity, completion and interruption

The review manifests identify the baseline Git commit. execution.json additionally
records hashes of every preprocessing Python/R source file, explicitly marking
the user-authorized uncommitted implementation. Validation requires those exact
source bytes and configuration; a later checkout cannot silently validate under
a different implementation. Future runs of the committed runner record their own actual commit and hashes;
acceptance does not rewrite either review bundle or its execution-time identity.

Canonical and external environment locks have distinct byte identities. The
canonical source lock enriches the original acquisition manifest with source and
R provenance; its acquisition_manifest_sha256 authenticates the external lock.
The external renv.lock has equivalent JSON content with original serialization.
The run configuration pins both external hashes and canonical lock hashes. The
gate separately audits all installed package files against authenticated package
archives; the runner checks lock identities and actual effective package versions.

An existing external root is permitted. Each invocation creates a unique
`attempts/.attempt-<section>-<uuid>` directory holding fit/transport logs,
validation evidence and a temporary bundle. Final `sections/<section-id>` must
be absent and is never overwritten. Payloads are closed, flushed and
read back before the final manifest is written. The complete bundle is validated
again against that manifest, then renamed on the same filesystem to the section
directory. Existing final sections are refused. A receipt under `receipts/` contains
the final manifest hash, elapsed time and normalization memory peak.

The six-file bundle is the authoritative artifact boundary. After promotion,
attempt directories and the surrounding gate directory may be deleted or kept
for debugging; successful validation does not depend on their existence. A
copied bundle retains its section directory name and needs only its six files,
the exact validator code/configuration, authenticated raw source and isolated
environment for full recorrection. The validator writes fresh readback evidence
to a separate external work directory without changing the copied bundle.

Readers reject .attempt paths, missing manifests, incomplete contents and failed
hashes. Failed attempts retain failure.json and never become finalized sections.
Partial scientific stages are not resumed: a new attempt is required. The
sequential launcher may reuse validated finalized bundles through its documented
fast integrity check. It deliberately revalidates completion rather than trusting a previous
process exit. Full-data depth remains 124 and primary_holdout_scoring_eligible
remains false; no holdout transformation is implemented.

## Tests and accepted-artifact comparison

Run the existing Python suite and R validation cases, then the synthetic-only
SCT gate. Synthetic artifacts and all real outputs remain outside Git. Mutation
tests exercise corrupted IDs, axes, mappings, values, coordinates, metadata,
means, group sizes, hashes, regimes, manifests, warnings, incomplete bundles,
failed fits and overwrite/promotion behavior.

The reusable `tests/compare_sct_bundle.py` command accepts the same bundle,
raw-source, environment, config and work-dir arguments as the validator. It
authenticates the accepted S00 RDS files against committed evidence, compares
logical values, cells, genes and effective fit arguments in R, then compares
canonical logical payload hashes with HDF5. It never fits SCT or modifies the
accepted artifacts. HDF5 and RDS file hashes are not expected to agree.

The integration command `tests/check_bundle_portability.py` accepts bundle,
raw-source, environment, config and work-dir arguments. It requires a six-file
copy and all original normalization/readback log paths to be absent, then runs
full independent validation and verifies the copy is byte-for-byte unchanged.

The [review report](audits/20261031_response_S00/summary.md) records measured
results, exact external locations and the isolation test. The prior S00 review
bundle was produced by uncommitted code and depended on external attempt logs;
it is superseded as review evidence and is not a future all-section S00 artifact.
The regenerated isolated bundle is accepted review evidence from uncommitted
code, not an all-section production artifact. Separately approved v2 production
recomputed all 19 sections under the committed generating identity recorded in
the receipt above. This does not relabel these review
artifacts or require them to validate under a new execution identity.
No remaining-section execution follows
automatically from a passing S00 gate.
