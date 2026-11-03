# S10 circular grid designs

User-requested design: all nine diameter/count combinations on the existing
4,712-cell half-population, keeping the accepted full 9,422-cell mesh fixed.
This is a coordinate-only design, not a fitted or scored experiment.

Diameter fractions are 1/24, 1/16 and 1/8 of the full modeled S10 population's
horizontal (center_x) extent, measured before subsampling or removing holes.
The canonical isotropic coordinate transform preserves circular shapes.
Centers occupy equally spaced interior positions on 4x3, 4x2 and 2x2 grids.
Centers stay fixed across diameters. Circles may cross the irregular tissue edge;
only existing selected cells inside them are removed. All circles contain cells;
no circles overlap. Closed-circle boundaries are included in the holdout.

See `S10-nine-configurations.png` and `configurations.json` for all counts,
centers, radii and source identities. Historical observations supplied only
membership/identity/coordinates, never expression responses. Their whole-file
hash and the canonical input hash were checked before extraction. Source-row
joins, cell names and coordinates matched exactly for all 4,712 selected cells.

Local external outputs are under
`C:/Users/andyb/Desktop/BSFM_ENVIRONMENTS/s10-hole-plots`:
`coordinates.npz`, `split-indices.npz`, the plot PNG/PDF and configuration JSON.
The split NPZ stores ordered canonical full-input row indices for both training
and held-out cells in every configuration. No mesh arrays were modified.

To reproduce the coordinate input on another machine, load the authenticated
canonical mirror's `s10-preparation-v2/prepared/model-input.npz` and the
historical `OBSERVATIONS.npz` registered in `docs/external-artifacts.json`.
Join historical source_row_indices to canonical source_row_indices in historical
order; verify matching cell_names and slocs. Save canonical slocs, cell_id and
source_row_indices plus the joined indices as subset_indices in coordinates.npz.
Run `python plot_configurations.py coordinates.npz OUTPUT_DIRECTORY` with NumPy
and Matplotlib. The recorded input hash authenticates this extraction.

Training-only response preparation and initialization, matched warped/flat fits,
and held-out prediction remain subsequent work. These plots authorize no claim
of predictive validation and do not merge the Layer-9 review into main.
