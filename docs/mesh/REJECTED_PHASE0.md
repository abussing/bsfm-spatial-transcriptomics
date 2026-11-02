# Rejected M3 / Phase-0 study receipt

Historical evidence only. The canonical mesh entry point is
[`bsfm.mesh.october26.build`](../../src/bsfm/mesh/october26.py), governed by the
[latent-warp decision](../decisions/ADAPTIVE_MESH_WARP_BASIS.md).

M3/Phase 0 attempted range-derived resolution and buffer choices using continuum
Matérn covariance agreement. It treated that agreement as a route to geometry
selection. The first S10 v1 attempt failed at string-array transport. The repaired
v2 attempt constructed the coarse candidate with **2,675 vertices**, then failed
the **covariance-root derivative identity check**. Zero candidates completed;
the remaining five were not run. The preserved
[failure receipt](audits/october26_S10_20261102/rejected-phase0.json) records the
external failed-run locations and failure-record identity. This cleanup does not
reopen or modify those artifacts.

The user rejected the range-derived geometry objective: the mesh is a
parsimonious basis for an unknown, learnable latent warp, not a certification of
infinite-domain covariance across extreme prior ranges. Practical repeated
sampling, smooth adaptive coverage and outward grading govern the chosen
October 26 construction. The derivative failure is a recorded experimental
failure, not a claim that all reusable numerical identities are invalid.
No Phase-0 v3, new sweep or automatic production selection is authorized.

Complete former implementation and detailed evidence remain in Git:

| Commit | Historical contents |
| --- | --- |
| `cfd00047d884021bed52194eb70189fd9cddc268` | M3 study design |
| `98edaf8b5fb1ec7cbd2534eea10a843221eef7ff` | Phase-0 harness and synthetic audit |
| `6572d0e1be5814d8026a98f5b45c7501a3706cb8` | Fine arm restricted to reference use |
| `4e362b6b3988e1b899d4250812ddfc4040beb819` | Transport correction; S10 v2 generating commit |
| `4f732ad08983e0b24aaba9fd99cabc1437e3c98a` | Last complete pre-cleanup tree, including former study source/configuration/schemas/tests and audits |

The active launcher, study-specific helpers, policies, schemas and tests are
removed. Reusable FEM, projector, full-spectrum, marginalization and diagnostic
helpers remain unchanged; their small numerical tests remain. These helpers do
not authorize another geometry-selection path. The accepted environment and its
restoration evidence retain their original `mesh-phase0-20261031` identity.
The [cleanup inventory](audits/active_cleanup_20261102/inventory.csv) records
every affected baseline file and its SHA-256.
