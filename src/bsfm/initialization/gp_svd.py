"""Conservative C3 GP-smooth-to-SVD port; lineage and limits in docs/initialization.

This module consumes an authenticated, centered genes-by-cells response. It
never updates that response, fits a sampler, or adds a sign convention to SVD.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import time
import warnings

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from threadpoolctl import threadpool_info, threadpool_limits

REPO = Path(__file__).resolve().parents[3]
CONFIG = REPO/'config/initialization/c3-gp-svd.json'
INPUT_KEYS = ('Y', 'slocs', 'cell_id', 'cell_names', 'source_row_indices',
              'gene_names', 'cell_type_names')


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def logical(a):
    """Shape/dtype plus ordered values; Unicode encoded as JSON UTF-8 strings."""
    a = np.asarray(a)
    if a.dtype.hasobject:
        raise ValueError('Object arrays are not permitted')
    if a.dtype.kind == 'U':
        value = json.dumps(a.tolist(), ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        dtype = 'utf8'
    else:
        dtype = a.dtype.newbyteorder('<').str
        value = np.asarray(a, dtype=dtype).tobytes(order='C')
    header = json.dumps({'shape': list(a.shape), 'dtype': dtype}, sort_keys=True).encode()+b'\n'
    return hashlib.sha256(header+value).hexdigest()


def identities(data):
    return {name: logical(data[name]) for name in INPUT_KEYS}


def load_input(path, contract):
    if contract['schema'] != 'bsfm.gpinit-input.v1' or contract['response'] != 'final_centered_Y':
        raise ValueError('Wrong input contract')
    if sha(path) != contract['source_sha256']:
        raise ValueError('Source hash mismatch')
    with np.load(path, allow_pickle=False) as bank:
        data = {name: bank[name] for name in INPUT_KEYS}
    if identities(data) != contract['arrays']:
        raise ValueError('Array identity/order mismatch')
    validate(data, 1, 1, 0)
    return data


def validate(data, factors, nfit, seed):
    for name, value in [('factors', factors), ('nfit', nfit), ('seed', seed)]:
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)):
            raise ValueError(name+' must be an integer')
    if factors < 1 or nfit < 1 or not 0 <= seed < 2**32:
        raise ValueError('Invalid factors/nfit/seed')
    y, xy, types = (np.asarray(data[k]) for k in ('Y', 'slocs', 'cell_id'))
    if y.ndim != 2 or min(y.shape) < 1 or xy.shape != (y.shape[1], 2):
        raise ValueError('Response/coordinate dimensions')
    g, n = y.shape
    if types.shape != (n,) or types.dtype.kind not in 'iu':
        raise ValueError('Type codes must be a one-dimensional integer axis')
    c = len(data['cell_type_names'])
    if not np.array_equal(np.unique(types), np.arange(c)):
        raise ValueError('Missing or noncontiguous types')
    if factors > min(c*g, n) or not np.isfinite(y).all() or not np.isfinite(xy).all():
        raise ValueError('Rank bound or nonfinite data')
    for name, length in [('gene_names', g), ('cell_names', n), ('cell_type_names', c)]:
        a = np.asarray(data[name])
        if a.shape != (length,) or a.dtype.kind != 'U' or len(np.unique(a)) != length or np.any(a == ''):
            raise ValueError('Invalid identity axis: '+name)
    rows = np.asarray(data['source_row_indices'])
    if rows.shape != (n,) or rows.dtype.kind not in 'iu' or np.any(rows < 0) or len(np.unique(rows)) != n:
        raise ValueError('Invalid source rows')


def fitting_points(types, nfit, seed):
    rng = np.random.RandomState(seed)
    choices = [rng.choice(cells, min(nfit, len(cells)), replace=False)
               for cells in [np.flatnonzero(types == c) for c in range(int(types.max())+1)]]
    return choices, rng


def kernel(spec):
    return (ConstantKernel(spec['constant'], tuple(spec['constant_bounds'])) *
            Matern(spec['length_scale'], tuple(spec['length_scale_bounds']), nu=spec['nu']) +
            WhiteKernel(spec['noise'], tuple(spec['noise_bounds'])))


def svd_seeds(fields, factors, floor):
    c, g, n = fields.shape
    stacked = fields.reshape(c*g, n).copy()
    stacked -= stacked.mean(axis=1, keepdims=True)
    left, singular, right = np.linalg.svd(stacked, full_matrices=False)
    raw = (left[:, :factors]*singular[:factors]).reshape(c, g, factors)
    loading = np.zeros_like(raw)
    eta = np.zeros_like(right[:factors])
    for k in range(factors):
        norm = max(float(np.linalg.norm(raw[:, :, k])), floor)
        loading[:, :, k] = raw[:, :, k]/norm
        eta[k] = right[k]*norm
    return stacked, singular, loading, eta


def fit(data, *, factors, nfit, seed, config=None):
    cfg = json.loads(CONFIG.read_text(encoding='utf-8')) if config is None else config
    validate(data, factors, nfit, seed)
    before = identities(data)
    y = np.asarray(data['Y'], dtype=np.float64).copy()
    xy = np.asarray(data['slocs'], dtype=np.float64)
    types = np.asarray(data['cell_id'], dtype=np.int64)
    g, n = y.shape
    c = len(data['cell_type_names'])
    means = np.stack([y[:, types == t].mean(axis=1) for t in range(c)])
    for t in range(c):
        y[:, types == t] -= means[t, :, None]
    choices, rng = fitting_points(types, nfit, seed)
    fields = np.zeros((c, g, n), dtype=np.float64)
    lengths = np.full((c, g), np.nan)
    variances = np.zeros((c, g))
    started = time.perf_counter()
    with threadpool_limits(limits=cfg['threads']), warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        for t, ix in enumerate(choices):
            for gene in range(g):
                gp = GaussianProcessRegressor(kernel=kernel(cfg['kernel']), **cfg['regressor'])
                gp.fit(xy[ix], y[gene, ix])
                fields[t, gene] = gp.predict(xy)
                try:
                    lengths[t, gene] = float(np.ravel(gp.kernel_.k1.k2.length_scale)[0])
                except Exception:
                    pass
                variances[t, gene] = fields[t, gene].var()
        finite = np.isfinite(lengths.ravel())
        ls, weights = lengths.ravel()[finite], variances.ravel()[finite]
        if len(ls) and weights.sum() > 0:
            order = np.argsort(ls)
            cumulative = np.cumsum(weights[order])
            theta = float(ls[order[np.searchsorted(cumulative, cumulative[-1]/2.0)]])
        elif len(ls):
            theta = float(np.median(ls))
        else:
            theta = cfg['diagnostic_fallback']
        stacked, singular, loading, eta = svd_seeds(fields, factors, cfg['loading_norm_floor'])
        subset = rng.choice(n, min(cfg['diagnostic_nfit'], n), replace=False)
        factor_ls = np.zeros(factors)
        for k in range(factors):
            gp = GaussianProcessRegressor(kernel=kernel(cfg['diagnostic_kernel']), **cfg['regressor'])
            gp.fit(xy[subset], eta[k, subset])
            try:
                factor_ls[k] = float(np.ravel(gp.kernel_.k1.k2.length_scale)[0])
            except Exception:
                factor_ls[k] = theta
        factor_ls = np.clip(factor_ls, *cfg['diagnostic_kernel']['length_scale_bounds'])
    reconstructed = loading.reshape(c*g, factors)@eta
    fitted = np.empty_like(y)
    for t in range(c):
        ix = np.flatnonzero(types == t)
        fitted[:, ix] = reconstructed[t*g:(t+1)*g, ix]
    result = dict(Lam_seed=loading, eta_seed=eta, theta_prior_mu=np.asarray(theta),
        field_ls=factor_ls, theta_seed=factor_ls.copy(), singular_values=singular[:min(20, len(singular))],
        seed_vs_smoothed_correlation=np.asarray(np.corrcoef(stacked.ravel(), reconstructed.ravel())[0, 1]),
        seed_vs_observed_correlation=np.asarray(np.corrcoef(y.ravel(), fitted.ravel())[0, 1]))
    if before != identities(data):
        raise RuntimeError('Input mutation')
    unit = loading.reshape(c*g, factors)
    report = dict(schema='bsfm.gpinit-diagnostics.v1', factors=factors, nfit=nfit, seed=seed,
        dimensions={'types':c,'genes':g,'cells':n}, elapsed_seconds=time.perf_counter()-started,
        maximum_input_recentering_mean=float(np.max(abs(means))),
        input_identities=before, fitting_indices=[ix.tolist() for ix in choices],
        diagnostic_fitting_indices=subset.tolist(),
        centered_surface_sha256=logical(stacked), surface_mean_max=float(np.max(abs(stacked.mean(axis=1)))),
        surface_norm=float(np.linalg.norm(stacked)), all_singular_values=singular.tolist(),
        truncation_error=float(np.linalg.norm(stacked-reconstructed)),
        loading_orthogonality_max=float(np.max(abs(unit.T@unit-np.eye(factors)))),
        eta_mean_max=float(np.max(abs(eta.mean(axis=1)))), eta_sd=eta.std(axis=1).tolist(),
        warnings=dict(Counter(type(w.message).__name__+': '+str(w.message) for w in caught)),
        output_logical_hashes={k:logical(v) for k,v in result.items()},
        python=platform.python_version(), platform=platform.platform(),
        packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','scikit-learn','joblib','threadpoolctl']},
        thread_limit=cfg['threads'], numerical_libraries=threadpool_info())
    return result, report


def save(directory, arrays, report, *, provenance):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(directory/'gpinit.npz', **arrays)
    with np.load(directory/'gpinit.npz', allow_pickle=False) as bank:
        if set(bank.files) != set(arrays) or any(not np.array_equal(bank[k], arrays[k], equal_nan=True) for k in arrays):
            raise RuntimeError('Saved seed readback mismatch')
    record = dict(report, provenance=provenance, output_sha256=sha(directory/'gpinit.npz'), status='pass')
    (directory/'certificate.json').write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return record


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',type=Path,required=True)
    parser.add_argument('--contract',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    for key in ['factors','nfit','seed']:parser.add_argument('--'+key,type=int,required=True)
    args=parser.parse_args()
    contract=json.loads(args.contract.read_text(encoding='utf-8'))
    data=load_input(args.input,contract)
    arrays,report=fit(data,factors=args.factors,nfit=args.nfit,seed=args.seed)
    save(args.output,arrays,report,provenance=dict(input=str(args.input.resolve()),
        input_sha256=sha(args.input),contract_sha256=sha(args.contract),
        config_sha256=sha(CONFIG),implementation_sha256=sha(__file__)))


if __name__=='__main__':main()
