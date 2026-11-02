# Bounded active-code cleanup proposal

Baseline: `4f732ad08983e0b24aaba9fd99cabc1437e3c98a`. This is a proposed,
uncommitted cleanup for review, not another scientific experiment.

The sole canonical mesh entry point is `bsfm.mesh.october26.build`. Its Python
and R implementation, configuration and complete transitive numerical dependency
closure remain byte-identical. The module CLI remains an S10 historical
regression utility, not an all-section launcher. No real meshes were generated.

## Inventory and boundaries

The [file inventory](inventory.csv) records baseline identities and A/B/C/D
classification. A comprises the builder, dependencies, configuration, regression
tests and accepted runtime/package locks; B comprises reusable numerical/resource helpers.
All A/B files are unchanged. In particular, `geometry.py` imports `support.py`,
so both remain even though the rejected study also used them. Their retained
diagnostic helpers are not an alternative launcher or a production selection
rule. The package `__init__.py` changes only its obsolete docstring.

The environment validator had one study-only metadata dependency. Its registry
hash check now reads the identical value from the already hash-authenticated
SCTransform run manifest, instead of the deleted study config. This is an
environment-check wiring change, not a package, mesh, numerical or tolerance
change. All other lines of that validator are unchanged. Historical environment
receipts continue to identify the earlier script bytes at their generating commit.

C comprises 14 deleted files: eight study-only source/bridge/input wrappers,
two configurations, three schemas and the mixed former test module. Its
authenticated-input wrapper was coupled to the removed study configuration;
canonical preprocessing authentication and the canonical builder are unchanged.
Fourteen independent numerical/resource tests were moved with exact method
bodies into `test_mesh_infrastructure.py`; the launcher/transport/candidate
tests were removed with their implementation. See [test retention](retained-tests.json).

Twenty-two D study-design/audit files are replaced by the single
[historical receipt](../../REJECTED_PHASE0.md). M1/M2 source recovery, accepted
environment/restoration evidence, and October 26 localization/reproduction/
acceptance receipts remain. Historical file inventories in those receipts still
describe their generating commits; they are not instructions to run removed code.
Live documentation links point to the canonical decision or rejected-study receipt.

The [import/reference inventory](references.json) records the pre-cleanup
source dependency graph and references to deleted files. The
[validation record](validation.json) records unchanged-file hashes, import/link
checks, test results and diff checks. The accepted environment's path retains
`phase0` as an immutable provenance label; no environment is rebuilt or renamed.

## Validation scope

Run the complete repository Python suite with `BSFM_MESH_INTEGRATION=1` using
the accepted mesh Python, plus the seven R validation cases. The integration
test reuses the unchanged environment validation scripts: two fresh R sessions
with the tiny 13-vertex/16-triangle fixture, projector/affine checks, semantic
repeat comparison, sparse R/Python/R roundtrip and index-corruption rejection.
The canonical JSON/Python/R 25-degree boundary regression remains unchanged.
No S10 reproduction, resolution sweep, all-section run or scientific study is
repeated during cleanup. Large logs and the complete proposed patch are under
the Git-ignored `artifacts/mesh_cleanup_20261102/` directory.
