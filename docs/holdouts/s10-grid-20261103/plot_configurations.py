"""Coordinate-only S10 hole design; no responses, fitting, or mesh changes."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

p = argparse.ArgumentParser()
p.add_argument('coordinates', type=Path)
p.add_argument('output', type=Path)
args = p.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
a = np.load(args.coordinates, allow_pickle=False)
xy = a['slocs'][:, ::-1]  # canonical [center_y, center_x] -> plotted [x, y]
ix = a['subset_indices']
assert xy.shape == (9422, 2) and ix.shape == (4712,)
assert len(np.unique(ix)) == 4712
subset = xy[ix]
lo, hi = xy.min(axis=0), xy.max(axis=0)
width = float(hi[0] - lo[0])
fig, axes = plt.subplots(3, 3, figsize=(14, 14), sharex=True, sharey=True)
configs, masks = [], {}
for row, count in enumerate((12, 8, 4)):
    nx, ny = {12: (4, 3), 8: (4, 2), 4: (2, 2)}[count]
    centers = np.array([(lo[0] + (hi[0]-lo[0])*x/(nx+1),
                         lo[1] + (hi[1]-lo[1])*y/(ny+1))
                        for y in range(1, ny+1) for x in range(1, nx+1)])
    for col, divisor in enumerate((24, 16, 8)):
        radius = width/(2*divisor)
        membership = ((subset[:, None, :] - centers[None, :, :])**2).sum(axis=2) <= radius**2
        held = membership.any(axis=1)
        name = f'circles{count}_diameter1of{divisor}'
        masks[name+'_heldout_full_indices'] = ix[held]
        masks[name+'_training_full_indices'] = ix[~held]
        assert not np.any(membership.sum(axis=1) > 1)
        conf = dict(id=name, circles=count, diameter_fraction=f'1/{divisor}',
                    radius=radius, centers_xy=centers.tolist(),
                    heldout=int(held.sum()), training=int((~held).sum()),
                    per_circle_counts=membership.sum(axis=0).tolist())
        configs.append(conf)
        ax = axes[row, col]
        ax.scatter(*xy.T, s=1, color='#d9dde3', rasterized=True)
        ax.scatter(*subset[~held].T, s=2, color='#346b94', rasterized=True)
        ax.scatter(*subset[held].T, s=4, color='#d34b31', rasterized=True)
        for j, center in enumerate(centers):
            ax.add_patch(Circle(center, radius, fill=False, color='#b63824', lw=1))
            ax.annotate(str(j+1), center, xytext=(0, 3), textcoords='offset points',
                        fontsize=6, ha='center', color='#8b2418')
        ax.set_aspect('equal')
        ax.set_title(f'{count} circles | diameter = width/{divisor}\n'
                     f'{held.sum():,} held out | {(~held).sum():,} training', fontsize=11)
        ax.tick_params(labelsize=8)
        if row == 2: ax.set_xlabel('center_x (fixed normalized frame)')
        if col == 0: ax.set_ylabel('center_y (fixed normalized frame)')
fig.suptitle('S10: circular holdouts on the existing 50% subset\n'
             'Blue: training   Orange: held out   Gray: other full-section cells\n'
             '4,712 selected cells; full 9,422-cell mesh stays fixed', fontsize=16, y=.995)
fig.tight_layout(rect=(0, 0, 1, .94))
fig.savefig(args.output/'S10-nine-configurations.png', dpi=180)
fig.savefig(args.output/'S10-nine-configurations.pdf')
plt.close(fig)
np.savez_compressed(args.output/'split-indices.npz', **masks)
report = dict(scope='coordinate-only design; no fit or prediction performed',
    full_cells=9422, selected_cells=4712, width_axis='center_x', width=width,
    source_native_scale=7551.6955652603265,
    coordinate_sha256=hashlib.sha256(args.coordinates.read_bytes()).hexdigest(),
    canonical_input_sha256='fc9478949f06d5c4c53e77caeb25426eba84b5df93a95c32335b638f912e83f3',
    historical_subset_sha256='c6356cc2da031e441c1955e831308cc1c3f87ac391845fa40feede1ba97ba4fc',
    unchanged_mesh_sha256='69c4df099766a7d393c570f7d77f6a85fbc88b0c9466f15049f85c3d3536bae0',
    selection='historical subset joined to canonical source_row_indices; names and coordinates exact',
    grid='interior equally spaced bounding-box grid; same centers across diameters',
    boundary='closed circles; Euclidean distance <= radius', configurations=configs)
(args.output/'configurations.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps([dict(id=c['id'], heldout=c['heldout'], per_circle=c['per_circle_counts']) for c in configs], indent=2))
