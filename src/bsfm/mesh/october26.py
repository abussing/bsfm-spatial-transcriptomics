"""Conservative October 26 mesh port and bounded historical regression.

No sampler, continuum selection, or resolution sweep. Historical input files
are read as data; no historical Python/R implementation is executed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy import sparse
from scipy.linalg import eigh
from scipy.io import mmread
from scipy.special import logsumexp

from .identities import REPO, file_record, logical, read_json, require, write_json
from .projectors import active, project, validate


def normalize_glia(coordinates):
    xy = np.asarray(coordinates, dtype=np.float64)
    require(xy.ndim == 2 and xy.shape[1] == 2 and len(xy) > 0,
            'Expected nonempty glial coordinates with two axes')
    require(np.isfinite(xy).all(), 'Nonfinite glial coordinates')
    origin = xy.min(axis=0)
    scale = float(np.ptp(xy, axis=0).max())
    require(scale > 0, 'Zero coordinate span')
    return (xy-origin)/scale, origin, scale


def historical_half_indices(xy, cell_type):
    """F/prepare_inputs.py:19-25,45-48; regression only, not a new thinning policy."""
    q = np.rint((xy-xy.min(0))/np.maximum(np.ptp(xy, axis=0), 1e-12)*65535).astype(np.int64)
    codes = np.zeros(len(xy), np.int64)
    for bit in range(16):
        codes += ((q[:, 0] >> bit) & 1) << (2*bit)
        codes += ((q[:, 1] >> bit) & 1) << (2*bit+1)
    groups = []
    for c in np.unique(cell_type):
        ids = np.flatnonzero(cell_type == c)
        groups.append(ids[np.lexsort((ids, codes[ids]))][::2])
    return np.sort(np.concatenate(groups))


def fem_matrices(vertices, triangles):
    """P/build_section_mesh.py:75-102; preserve assembly/reduction order."""
    n = len(vertices)
    rows, cols, mv, gv, areas = [], [], [], [], []
    require(triangles.ndim == 2 and triangles.shape[1] == 3,
            'Triangle shape')
    require(triangles.dtype.kind in 'iu' and triangles.min() >= 0
            and triangles.max() < n, 'Zero-based triangle indices required')
    for tri in triangles:
        p = vertices[tri]
        twice = np.linalg.det(np.asarray([[1., *p[0]], [1., *p[1]], [1., *p[2]]]))
        area = .5*abs(twice)
        require(area > 1e-13, 'Degenerate triangle')
        areas.append(area)
        b = np.asarray([p[1, 1]-p[2, 1], p[2, 1]-p[0, 1], p[0, 1]-p[1, 1]])
        c = np.asarray([p[2, 0]-p[1, 0], p[0, 0]-p[2, 0], p[1, 0]-p[0, 0]])
        m = (area/12.)*(np.ones((3, 3))+np.eye(3))
        g = (np.outer(b, b)+np.outer(c, c))/(4.*area)
        for i in range(3):
            for j in range(3):
                rows.append(int(tri[i])); cols.append(int(tri[j]))
                mv.append(float(m[i, j])); gv.append(float(g[i, j]))
    def matrix(values):
        result = sparse.coo_matrix((values, (rows, cols)), shape=(n, n)).tocsr()
        result.sum_duplicates()
        return result
    return matrix(mv), matrix(gv), np.asarray(areas)


def polynomial_fem(mass, stiffness):
    """F/prepare_inputs.py:81-91, including its roundoff clamp."""
    m, g = mass.toarray(), stiffness.toarray()
    ev, u = eigh(g, m)
    require(ev.min() >= -2e-10*max(1., abs(ev).max()), 'Negative FEM eigenvalue')
    ev = np.maximum(ev, 0)
    left = m@u
    terms = [m, g]
    for power in range(2, 7):
        gp = (left*ev[None, :]**power)@left.T
        terms.append((gp+gp.T)*.5)
    return terms


def spectral_artifact(terms, tolerance=2e-10):
    """Same full-spectrum authentication as historical spectral loader, no JAX."""
    m, g = terms[:2]
    ev, u = eigh(g, m)
    orth = relative(u.T@m@u, np.eye(len(u)))
    residual = relative(g@u, m@(u*ev[None, :]))
    diagonals, errors = [], []
    for term in terms:
        transformed = u.T@term@u
        diagonal = np.diag(transformed).copy()
        errors.append(relative(transformed, np.diag(diagonal)))
        require(diagonal.min() >= -2e-12*max(1., abs(diagonal).max()),
                'Negative modal diagonal')
        diagonals.append(np.maximum(diagonal, 0))
    require(max(orth, residual, *errors) < tolerance, 'FEM spectral identity')
    return u, np.stack(diagonals), dict(orthogonality=orth,
        eigen_residual=residual, simultaneous_diagonal_errors=errors,
        full_modes=len(ev), truncation=False)


def marginal_root(u, modal_diagonals, indices, ell):
    require(np.isfinite(ell) and ell > 0, 'Positive range required')
    require(len(np.unique(indices)) == len(indices)
            and np.all((indices >= 0) & (indices < len(u))), 'Active index identity')
    logs = np.full_like(modal_diagonals, -np.inf)
    positive = modal_diagonals > 0
    logs[positive] = np.log(modal_diagonals[positive])
    coeff = np.asarray([math.comb(6, j)/(20*np.pi) for j in range(7)])
    powers = 2-2*np.arange(7)
    logq = logsumexp(np.log(coeff)[:, None]
                    + powers[:, None]*np.log(np.sqrt(40)/ell)+logs, axis=0)
    sd = np.exp(-.5*logq)
    b = u[indices]*sd[None, :]
    r = np.linalg.qr(b.T, mode='reduced')[1]
    root = (np.where(np.diag(r) < 0, -1., 1.)[:, None]*r).T
    require(np.isfinite(root).all() and np.all(np.diag(root) > 0), 'Invalid QR root')
    return root, sd


def warp_cells(projector, vertex_values, *, coordinates=None):
    """Direct W by default; coordinates+P@displacement only for mechanical tests."""
    require(vertex_values.shape == (projector.shape[1], 2), 'Two vertex fields required')
    result = np.asarray(projector@vertex_values)
    if coordinates is not None:
        require(coordinates.shape == result.shape, 'Coordinate shape')
        result = coordinates+result
    return result


def relative(a, b):
    return float(np.linalg.norm(a-b)/max(np.linalg.norm(b), np.finfo(float).tiny))


def dense_mm(path):
    a = mmread(path)
    return a.toarray() if sparse.issparse(a) else np.asarray(a)


def build(cells, inherited_vertices, inherited_triangles, environment, config, destination,
          *, runtime_lock=None, rscript=None):
    """One construction, with the historical bounded h adaptation inside R.

    An explicit lock selects an independently validated runtime. An optional
    executable path relocates that runtime without changing its pinned identity.
    Neither option establishes package or cross-platform mesh equivalence.
    """
    destination = Path(destination).resolve()
    require(not destination.exists(), 'Refusing existing mesh output')
    lock = Path(runtime_lock) if runtime_lock is not None else REPO/'environment/mesh/runtime-lock.json'
    runtime = read_json(lock)['R']
    executable = str(Path(rscript).resolve()) if rscript is not None else runtime['path']
    require(file_record(executable) == {k: runtime[k] for k in ('bytes', 'sha256')},
            'R runtime executable identity')
    command = [executable, '--vanilla', str(Path(__file__).with_name('october26_builder.R')),
               str(Path(environment).resolve()), str(Path(config).resolve()),
               str(Path(cells).resolve()), str(Path(inherited_vertices).resolve()),
               str(Path(inherited_triangles).resolve()), str(destination)]
    env = os.environ.copy()
    env.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1',
               LANG='C', LC_ALL='C', TMP=str(destination.parent),
               TEMP=str(destination.parent), TMPDIR=str(destination.parent))
    start = time.perf_counter()
    proc = subprocess.run(command, env=env, capture_output=True)
    log = proc.stdout+proc.stderr
    (destination.parent/'construction.log').write_bytes(log)
    require(proc.returncode == 0 and b'stack imbalance' not in log.lower(),
            f'Construction failed (exit {proc.returncode}): {log[-2000:]!r}')
    return dict(command=command, seconds=time.perf_counter()-start, exit_code=proc.returncode,
                runtime_lock=dict(path=str(lock.resolve()), **file_record(lock)),
                runtime_executable=dict(path=executable, **file_record(executable)),
                log=file_record(destination.parent/'construction.log'))


def reproduce(bundle, environment, output, config):
    """One S10 regression from exact historical data, never executing legacy code."""
    bundle, output, config = Path(bundle), Path(output), Path(config)
    cfg = read_json(config)
    require(cfg == read_json(REPO/'config/mesh/october26-warp-basis.json'), 'Frozen config required')
    require(not output.exists(), 'Fresh reproduction root required')
    section = 'S10__WT5'
    src, ref = bundle/'source_geometry'/section, bundle/'preview'/section
    prepared = bundle/'inputs'/section
    paths = [src/n for n in ('cells.csv', 'mesh_loc.csv', 'mesh_tv.csv',
             'OBSERVATIONS_BASE.npz', 'INPUT_CONTRACT.json')]
    paths += [ref/n for n in ('mesh_loc.csv', 'mesh_tv.csv', 'A_proj.mtx', 'CERTIFICATE.json')]
    paths += [prepared/'mesh'/n for n in ('mesh_loc.csv','mesh_tv.csv','A_proj.mtx','active_indices.csv','fem_C.mtx')]
    paths += [prepared/'mesh'/f'fem_g{j}.mtx' for j in range(1, 7)]
    paths += [prepared/'INPUT_CERTIFICATE.json', prepared/'OBSERVATIONS.npz']
    inputs = {str(p): file_record(p) for p in paths}  # missing dependencies fail before output creation
    cert = read_json(prepared/'INPUT_CERTIFICATE.json')
    for name, expected in cert['mesh_hashes'].items():
        require(file_record(prepared/'mesh'/name)['sha256'] == expected, 'Historical mesh hash: '+name)
    require(file_record(src/'OBSERVATIONS_BASE.npz')['sha256'] == cert['source_sha256'], 'Source observation identity')
    require(file_record(prepared/'OBSERVATIONS.npz')['sha256'] == cert['observation_sha256'], 'Retained observation identity')
    # Select only geometry and identity members; no expression array is opened.
    with np.load(src/'OBSERVATIONS_BASE.npz', allow_pickle=False) as z:
        xy, types = z['slocs'], z['cell_id']
        source_rows = z['source_row_indices']
    keep = historical_half_indices(xy, types)
    with np.load(prepared/'OBSERVATIONS.npz', allow_pickle=False) as z:
        np.testing.assert_array_equal(source_rows[keep], z['source_row_indices'])
        np.testing.assert_array_equal(xy[keep], z['slocs'])
        expected_active = z['active_indices']
        expected_aa = z['A_active']
    require(len(xy) == 9422 and len(keep) == 4712, 'Historical S10 population')
    output.mkdir(parents=True)
    start = time.perf_counter()
    write_json(output/'input-inventory.json', inputs)
    execution = build(src/'cells.csv', src/'mesh_loc.csv', src/'mesh_tv.csv',
                      environment, config, output/'geometry')
    geo = read_json(output/'geometry/geometry.json')
    v = np.loadtxt(output/'geometry/mesh_loc.csv', delimiter=',', skiprows=1)
    t = np.loadtxt(output/'geometry/mesh_tv.csv', delimiter=',', skiprows=1, dtype=np.int64)
    a = mmread(output/'geometry/A_proj.mtx').tocsr()
    fullactive = active(a)
    ah = a[keep].tocsr(); halfactive = active(ah)
    require((len(v), len(t), len(fullactive), len(halfactive)) == (371, 708, 168, 167),
            'S10 historical mesh counts differ; no tuning permitted')
    refv = np.loadtxt(ref/'mesh_loc.csv', delimiter=',', skiprows=1)
    reft = np.loadtxt(ref/'mesh_tv.csv', delimiter=',', skiprows=1, dtype=np.int64)
    np.testing.assert_array_equal(t, reft)
    np.testing.assert_allclose(v, refv, atol=cfg['regression_geometry_atol'], rtol=0)
    refa = mmread(ref/'A_proj.mtx').tocsr()
    require((a != 0).astype(int).__ne__((refa != 0).astype(int)).nnz == 0, 'Projector support mismatch')
    projector_error = float(abs(a-refa).max())
    require(projector_error < cfg['projector_tolerance'], 'Historical projector values')
    np.testing.assert_array_equal(halfactive, expected_active)
    np.testing.assert_allclose(ah[:, halfactive].toarray(), expected_aa, atol=cfg['projector_tolerance'], rtol=0)
    projection = validate(a, v, xy, cfg['projector_tolerance'])
    independent = project(v, t, xy, cfg['projector_tolerance'])
    independent_error = float(abs(independent-a).max())
    require(independent_error < cfg['projector_tolerance'], 'Independent projector disagreement')
    m, g, areas = fem_matrices(v, t)
    terms = polynomial_fem(m, g)
    refterms = [dense_mm(prepared/'mesh'/'fem_C.mtx')]
    refterms += [dense_mm(prepared/'mesh'/f'fem_g{j}.mtx') for j in range(1, 7)]
    fem_errors = [relative(x, y) for x, y in zip(terms, refterms)]
    require(max(fem_errors) < cfg['regression_fem_relative_tolerance'], 'Historical FEM disagreement')
    u, diags, spectral = spectral_artifact(terms, cfg['spectral_tolerance'])
    identities = {}
    for label, proj, idx in [('full_observations', a, fullactive), ('historical_half', ah, halfactive)]:
        root, sd = marginal_root(u, diags, idx, cfg['mechanical_check_range'])
        fullcov = (u*sd)@(u*sd).T
        activecov = fullcov[np.ix_(idx, idx)]
        root_error = relative(root@root.T, activecov)
        factor_error = relative((proj@u)*sd, (proj[:, idx]@u[idx])*sd)
        require(max(root_error, factor_error) < cfg['spectral_tolerance'], 'Exact marginalization identity')
        identities[label] = dict(root_covariance_relative_error=root_error,
                                 all_observation_full_active_factor_error=factor_error)
    zero_error = float(abs(warp_cells(a, np.zeros_like(v), coordinates=xy)-xy).max())
    displacement = np.column_stack((.01+v[:, 0]*.02, -.03+v[:, 1]*.04))
    expected_displacement = np.column_stack((.01+xy[:, 0]*.02, -.03+xy[:, 1]*.04))
    affine_displacement_error = float(abs(warp_cells(a, displacement)-expected_displacement).max())
    require(zero_error == 0 and affine_displacement_error < cfg['projector_tolerance'], 'Warp interpolation')
    arrays = dict(mesh_vertices=v, triangles=t, A_full=a.toarray(),
                  active_indices_full=fullactive, inactive_indices_full=np.setdiff1d(np.arange(len(v)), fullactive),
                  A_active=a[:, fullactive].toarray(), source_rows=source_rows,
                  slocs=xy, cell_type=types, historical_half_rows=keep,
                  historical_half_active=halfactive, historical_half_A_active=ah[:, halfactive].toarray(),
                  spectral_U=u, modal_diagonals=diags)
    arrays.update({('fem_C' if j == 0 else f'fem_g{j}'): x for j, x in enumerate(terms)})
    np.savez_compressed(output/'sampler-facing.npz', **arrays)
    # Independently reopen serialized arrays with explicit shape/dtype/logical hashes.
    axes = {k: dict(shape=list(x.shape), dtype=x.dtype.str, sha256=logical(x)) for k, x in arrays.items()}
    with np.load(output/'sampler-facing.npz', allow_pickle=False) as z:
        for key in arrays:
            require(logical(z[key]) == axes[key]['sha256'], 'Closed-file array identity')
    unchanged = all(file_record(p) == record for p, record in inputs.items())
    require(unchanged, 'Historical input changed during regression')
    report = dict(schema_version=1, status='PASS', scope='historical mechanical regression only; pending review',
        section=section, geometry_cells=len(xy), geometry_type_counts=np.bincount(types).tolist(),
        historical_retained_cells=len(keep), retained_type_counts=np.bincount(types[keep]).tolist(),
        vertices=len(v), triangles=len(t), active_full=len(fullactive), active_half=len(halfactive),
        configuration=file_record(config), source_identity={str(Path(__file__)):file_record(__file__),
            str(Path(__file__).with_name('october26_builder.R')):file_record(Path(__file__).with_name('october26_builder.R'))},
        construction=execution, geometry=geo, geometry_max_difference=float(abs(v-refv).max()),
        triangles_exact=True, projector_max_difference=projector_error, projector=projection,
        independent_projector_max_difference=independent_error, fem_relative_errors=fem_errors,
        spectral=spectral, exact_marginalization=identities, zero_displacement_error=zero_error,
        affine_displacement_error=affine_displacement_error, arrays=axes,
        output=file_record(output/'sampler-facing.npz'), index_base=0, axis_order=cfg['axis_order'],
        coordinate_units=cfg['units'], historical_inputs_unchanged=unchanged,
        total_seconds=time.perf_counter()-start, no_sampler_executed=True,
        no_continuum_selection=True)
    write_json(output/'report.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-bundle', required=True)
    parser.add_argument('--environment', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--config', default=str(REPO/'config/mesh/october26-warp-basis.json'))
    args = parser.parse_args()
    try:
        result = reproduce(args.historical_bundle, args.environment, args.output, args.config)
    except Exception as exc:
        out = Path(args.output)
        if out.is_dir() and not (out/'failure.json').exists():
            write_json(out/'failure.json', dict(status='FAIL', error=repr(exc)))
        raise
    print(json.dumps({k: result[k] for k in ('status','vertices','triangles','active_full','active_half','total_seconds')}))


if __name__ == '__main__':
    main()
