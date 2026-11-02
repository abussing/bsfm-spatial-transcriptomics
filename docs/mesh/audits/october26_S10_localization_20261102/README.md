# Bounded S10 localization and one corrected rerun

The corrected implementation and evidence were subsequently accepted for
canonicalization; see the [acceptance record](../october26_acceptance_20261102/README.md).
The measurements and execution scope below describe the original review run.

**An exact argument-type defect was found and corrected. The one authorized
rerun passed.** Nothing was committed or promoted. The user's clarification
remains controlling: 371 vertices is a historical regression observation, not a
scientific requirement. The objective is a useful, smooth, parsimonious warp
basis with outward coarsening and practical active dimension.

## Cause, correction and evidence

The historical R literal `min.angle=25` is a double. JSON parsing produced an
integer `25` in the port. The fmesher 0.7.0 native options reader accepts
`Rcpp::NumericVector` for `rcdt_min_angle`; an integer does not replace its
21-degree default. The existing failed port mesh measured 21 degrees, while
the historical mesh requested/measured 25 degrees.

Only this construction change was made:

```r
cfg$minimum_angle <- as.double(cfg$minimum_angle)
```

The frozen configuration file remained byte-identical, SHA-256
`ea6fab398526bd2801bdbdc2972395a24e202f6294083082d80a4f75c8abcf73`.
No h, edge target, hull, boundary, tolerance, population or environment changed.
The added regression evaluates the actual R builder prefix and fmesher option
handler without constructing a mesh. All eight bounded tests passed.

The narrow package-interface check used the already cached, authenticated
official fmesher source archive (no download or filesystem search):
`environment/mesh/r-source-lock.json` records SHA-256
`6a1c4e69c5d2a235edcc3a613cb0cff0015ceee78b65c2d342bc05e12ff8a185`.
Member `fmesher/src/Rcpp_interface.cc:78–86,105–128` shows the type check,
default and assignment. The installed `handle_rcdt_options_inla` preserves the
integer type passed by JSON; the corrected actual builder sends double 25.
The identical post-fix output, with no other construction change, localizes the
observed difference to that boundary.

## Coordinates and identities: exact match

Both builders read F `source_geometry/S10__WT5/cells.csv` in its original order.
Here F is `D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1`.
The port's retained pre-run inventory matches those exact historical file bytes.

R's decoded CSV coordinates and `OBSERVATIONS_BASE.npz["slocs"]` are bitwise
equal, shape `(9422,2)`, maximum difference **0**. The coordinate logical hash
on both sides is:

`1e1d4d754c6cf4149b25236f04ffd8055815379ab2adf0863026b92c364a41d7`

Unique source-row hash:
`ee20cd625176608ce024766ef5407a728deb2c8c63e5bbe32ab6aee9ab0064d3`.
Unique ordered cell-ID hash:
`d5a96d66f6ef145150793599a3313acaf54f452b8cd9b519f42d6a41a604d9b8`.
The historical 4,712-cell subset joins exactly by source row, cell ID and
coordinates. The CSV itself contains x/y/type, not independent cell-ID fields;
identity linkage is via the exact ordered coordinate/type sequence and NPZ axes.

The recorded transform is componentwise origin
`[-76.71150369109931, 384.4526611067433]`, maximum glial span
`7551.6955652603265`. Both builds consume already-normalized locations; neither
recalculates the transform. These are historical metadata, not a new raw-source
normalization audit. The historical `coordinate_scale_microns` field name does
not authenticate physical units. Canonical units remain `source_native`.

## Inherited far boundary: same source and hash on both sides

The exact source for historical and port construction is:

```text
F/source_geometry/S10__WT5/mesh_loc.csv
F/source_geometry/S10__WT5/mesh_tv.csv
```

| Input | Bytes | SHA-256, historical and port |
| --- | ---: | --- |
| mesh_loc.csv | 32,082 | fbca0dd7f8007010f710b8a94138cbdc83b01b4bfc4092ba83ee2f04a1957e6d |
| mesh_tv.csv | 14,357 | 2bf966a021459d8bfa5f244ccacc981d9e02ab1e24737dbe3b474577692530bc |

The same ordered-edge extraction gives 25 inherited boundary vertices.
Direct R extraction and an independent Python extraction agree:

- Ordered float64 boundary vertices:
  `9de075471e267eebed5afd6e94e306ec4cabb7aa7759ee842e7f557aa5e045ac`.
- Ordered local zero-based int64 edges:
  `210ff4dd522be853ce8d56bcb7095e49bc62a3ee8665f9cc51cd87df16c1f39c`.

The final historical boundary had 32 vertices, versus 29 in the pre-fix port,
because of different subdivision. Both retained the same polygon: maximum
boundary-vertex distance to the inherited segments was 6.21e-17, and every
inherited vertex lay on each output boundary. Bounding boxes were identical.
Thus differing boundary subdivision was an output difference, not a substituted
far-boundary input. These hashes use the existing dtype/shape/C-order logical
encoding; exact file hashes are recorded separately.

## Geometry inputs and recorded limits

| Input | Comparison before correction |
| --- | --- |
| Full geometry population / first-stage locations | Exact same ordered 9,422 glial positions; hash above. |
| Tissue hull and .02/.18/.45 polygons | Same code-level construction and parameters; original polygon arrays/order hashes were not saved. No hull was rebuilt for this comparison. |
| Stages 2–4 locations | Both use `rbind(xy, previous_mesh$loc[,1:2])`; intermediate arrays and hashes were not saved. |
| Internal constraints | Both retain preceding mesh boundary and interior segments as internal constraints. Final RDS segments exist, but are not original per-stage snapshots. |
| h attempts | 0.13, then 0.11290451085509637. |
| Cutoff | 0.45*h: 0.0585, then 0.05080702988479337. |
| Selected edge targets | 0.11290451085509637 / 0.20 / 0.30 / 0.55. |
| Minimum angle | Historical double 25; port integer 25 caused effective 21. Corrected to double 25. |
| extend / concavity / resolution / epsilon | FALSE / .12 / 150 / .006; equal values. Resolution is JSON integer versus historical double, unchanged in the successful rerun. |
| fmesher | Historical certificate and current library both 0.7.0. |
| R | Historical RDS writer metadata and current R both 4.5.3; RDS metadata is not a full historical session record. |
| Matrix | Port 1.7-4; historical version not found in the bounded A/F evidence. |

A has only the three original S00/S12/S14 previews. F's S10 source/preview
directories contain final meshes/certificates, not stage snapshots. A/F audit
and work-log records do not supply the missing per-stage vertex/triangle
counts. The final RDS objects preserve constraint segments, not all original
stage polygons and location arrays. No search outside the named historical
roots was made. Package-interface inspection was confined to the known locked
runtime and its already recorded source archive.

## Attempt selection and rerun

Both implementations keep the attempt closest to 175 full-cell active vertices,
stop when within 150–200, and select attempt 2 in this case. The selection uses
all 9,422 cells, never the thinned subset.

| Attempt | h | Historical full active / total | Pre-fix full active / total | Corrected full active / total |
| --- | ---: | ---: | ---: | ---: |
| 1 | .13 | 132 / 313 | 132 / 283 | 132 / 313 |
| 2, selected | .11290451085509637 | 168 / 371 | 167 / 330 | 168 / 371 |

Selected historical and corrected meshes have 708 triangles. Full active count
is 168; the historical 4,712-cell subset has 167 active vertices on the same
geometry. No new canonical observation-thinning decision is implied.

The single corrected run used the previous documented command with only the
fresh destination changed to:

`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_EXPERIMENTS\mesh_october26_S10_angle_fix_20261102`

The machine-local failed predecessor remains unchanged. Corrected vertices CSV,
triangles CSV, full projector Matrix Market and mesh RDS are **byte-identical**
to the historical files. FEM C/G1…G6 relative discrepancies are at most 6.23e-15.
The full and historical-half marginal-root checks have maximum relative error
8.32e-16; full-to-active projected spectral factors agree exactly. Zero
displacement changes no coordinates; affine displacement error is 4.34e-17.
Construction took 11.928 seconds; complete regression took 18.904 seconds.

The attained minimum angle is 25 degrees. The four historical spatial zones
have median triangle mean-edge lengths **.06922 / .09702 / .14873 / .21761**,
verified from the identical reproduced geometry and historical zone table.
This establishes the intended outward coarsening and mechanical handoff, not an
unknowable true warp or optimal statistical resolution. A future production
builder must not treat S10's particular vertex count as a universal requirement.

## Preserved records and scope

- [comparison.json](comparison.json): pre-rebuild coordinate, boundary and identity comparisons.
- [before-fix-mechanics.json](before-fix-mechanics.json): read-only checks on the existing 330-vertex mesh.
- [rds-writer-metadata.json](rds-writer-metadata.json): historical/current RDS writer versions.
- [localization.json](localization.json): cause, unchanged settings, exact output hashes and limits.
- [corrected-reproduction.json](corrected-reproduction.json): byte-identical copy of the corrected external report, including array shapes/hashes and exact command.

No parameter study, Phase-0 v3, all-section regeneration, fixed-artifact fallback,
GP initialization, sampler, holdout or HPC work occurred. The port remains an
uncommitted review proposal. Useful interpolation/mechanical tests and warp-flow
documentation are retained. The next action is review, not automatic promotion.
