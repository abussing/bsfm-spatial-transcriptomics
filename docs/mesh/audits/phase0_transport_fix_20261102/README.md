# Phase-0 input-transport correction

Baseline: `6572d0e1be5814d8026a98f5b45c7501a3706cb8`.
Scope: input serialization only. No real S10 rerun occurred in this correction
gate, and the future `mesh_phase0_S10_v2` root has not been created.

The failed S10 v1 attempt stopped before mesh construction because HDF5 UTF-8
IDs and axis labels loaded through `h5py.asstr()` were NumPy object arrays.
The transport writer saved those object arrays, while the worker correctly
refused to load them with `allow_pickle=False`. This was an implementation
defect, not evidence about covariance accuracy or computational feasibility.

`write_transport` now validates `all_ids`, `model_ids` and `axis_order` at the
writing boundary and converts them to explicit fixed-width NumPy Unicode.
Before writing it requires one-dimensional arrays, Python/NumPy strings only,
exact conversion with order preserved, unique all-cell/model-cell IDs, and
exact axis order `["center_y", "center_x"]`. Width is determined from the
longest original string; no normalization, sorting, trimming or coercion of
non-string values is allowed. Remaining object arrays are rejected. Both
`np.savez` and the unchanged worker `np.load` use `allow_pickle=False`.

The complete suite passed **119 tests, zero failures/errors/skips**, in
84.394 seconds: the existing 112 tests plus seven transport regression/rejection
tests. The [full log](tests.txt) and [validation record](validation.json) retain
the results, source hashes, unchanged configuration identities, environment
authentication and failed-v1 inventory.

The regression exercises the actual path:

```text
HDF5 UTF-8 datasets
  -> authenticated load_bundle / h5py.asstr object arrays
  -> actual phase0.run transport-writing boundary
  -> inputs.npz
  -> fresh Python process: np.load(..., allow_pickle=False)
```

It compares every transported identity in order as exact UTF-8 bytes and
length-prefixed logical hashes. It also compares all numeric transport arrays'
dtypes, shapes and C-order bytes. Every loaded array must be non-object, and
the three string arrays must have fixed-width Unicode dtype. The fixture
includes variable lengths, non-ASCII characters, a combining character, a
non-BMP character and trailing whitespace. Separate tests reject invalid
dimensions/types, duplicate identities, changed axis order, lossy conversion
and object arrays in other fields. No real meshing is invoked by this regression.

The complete suite also repeats the existing synthetic geometry/FEM/derivative
checks in fresh processes. Its scientific payload hashes and per-range semantic
hashes match both the previous reviewed results and the fresh repeat. Mesh
construction, scientific settings, candidates, tolerances, probes and resource
limits are unchanged. Full mesh-environment and shared-R runtime content hashes
still match their accepted identities.

Synthetic artifacts remain outside Git at this machine-local location:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_phase0_transport_fix_20261102
```

The failed real-run root remains unchanged:

```text
C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_phase0_S10_v1
```

All **nine files (2,452,525 bytes)** have identical before/after SHA-256 hashes,
sizes and modification timestamps, and the directory inventory is unchanged.
V1 still records failure and has no final manifest. It was not repaired,
promoted or retried. The [harness guide](../../PHASE0_HARNESS.md) documents the
future fresh-v2 command, which requires review of the exact corrected commit.
