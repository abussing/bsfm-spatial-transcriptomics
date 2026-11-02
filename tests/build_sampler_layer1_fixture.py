"""Explicit, bounded reference acquisition; never imports the historical monolith.

Only seven function AST nodes from two SHA-authenticated selected files execute.
Run explicitly with --source-root; normal unit tests read the small saved fixture.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy.linalg import cho_solve, solve_triangular
from threadpoolctl import threadpool_info, threadpool_limits

from bsfm.sampler import conjugate, shrinkage, px

SOURCES = {
    'c3_established_functions.py': ('828eef737fd36a47ec349837a936fc6ba49ffb0bec9fe556c08f502baa43e946',
        {'compute_Yhat': (2849, 2869), 'compute_qgk': (2817, 2846),
         'sample_Lambda_twostage': (6936, 7026), 'sample_sigma2_twostage': (7193, 7216),
         'sample_phi': (3886, 3913), 'sample_delta_tau': (3859, 3879)}),
    'run_c3full_fixed_profile_nuts.py': ('eb452c4c419a7ab55658439fa0105ea609b9eecd6e09b1c27c976c8d5da41c49',
        {'refresh_alpha_gauge': (182, 230)})}


def serial(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, (tuple, list)):
        return [serial(x) for x in value]
    if isinstance(value, dict):
        return {k: serial(v) for k, v in value.items()}
    return value


def rng_hash(state):
    return hashlib.sha256(json.dumps(serial(state), sort_keys=True).encode()).hexdigest()


def historical_functions(root):
    namespace = dict(np=np, cho_solve=cho_solve, solve_triangular=solve_triangular)
    identities = []
    for name, (expected, functions) in SOURCES.items():
        path = root/name; content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != expected:
            raise ValueError('Historical source hash mismatch: '+name)
        tree = ast.parse(content.decode('utf-8-sig'))
        selected = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in functions]
        if {n.name: (n.lineno, n.end_lineno) for n in selected} != functions:
            raise ValueError('Historical function scope mismatch')
        constants = []
        if name == 'run_c3full_fixed_profile_nuts.py':
            constants = [n for n in tree.body if isinstance(n, ast.Assign)
                         and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                         and n.targets[0].id in ('MU_LOG_ALPHA', 'VAR_LOG_ALPHA')]
            if [(n.targets[0].id, n.lineno) for n in constants] != [('MU_LOG_ALPHA', 43), ('VAR_LOG_ALPHA', 45)]:
                raise ValueError('PX source constant scope mismatch')
        # Only the seven functions and two authenticated PX constant assignments.
        # No module imports, driver main or experimental code are evaluated.
        exec(compile(ast.Module(body=constants+selected, type_ignores=[]), str(path), 'exec'), namespace)
        identities.append(dict(path=str(path), bytes=len(content), sha256=expected,
                               functions={k: list(v) for k, v in functions.items()}))
    return namespace, identities


def port_functions():
    return {name: getattr(module, name) for module, names in [
        (conjugate, ['compute_Yhat', 'sample_Lambda_twostage', 'sample_sigma2_twostage']),
        (shrinkage, ['compute_qgk', 'sample_phi', 'sample_delta_tau']),
        (px, ['refresh_alpha_gauge'])] for name in names}


def evaluate(functions, inputs, seed, order='C'):
    d = {k: np.array(v, dtype=np.float64, order=order) for k, v in inputs.items() if k != 'counts'}
    counts = inputs['counts']; stops = np.cumsum(counts); starts = np.r_[0, stops[:-1]]
    slices = [slice(int(a), int(b)) for a, b in zip(starts, stops)]
    c, g, k = d['loading'].shape
    before = {name: value.copy() for name, value in d.items()}
    saved_rng = np.random.get_state()
    try:
        np.random.seed(seed); rng = np.random.default_rng(seed+3003)
        yhat = functions['compute_Yhat'](d['loading'], d['eta'], slices)
        q = functions['compute_qgk'](d['loading'], d['s'], c)
        lam = functions['sample_Lambda_twostage'](d['Y'], d['eta'], d['sigma2'],
            np.ones_like(d['Y']), d['alpha'], d['phi'], d['tau'], d['s'], slices)
        updated_yhat = functions['compute_Yhat'](lam, d['eta'], slices)
        sigma2 = functions['sample_sigma2_twostage'](d['Y'], updated_yhat,
            np.ones_like(d['Y']), 2., .25*np.var(d['Y'], axis=1))
        updated_q = functions['compute_qgk'](lam, d['s'], c)
        phi = functions['sample_phi'](updated_q, d['alpha'], d['tau'], c, g, k, 1.5, 1.5)
        delta, tau = functions['sample_delta_tau'](updated_q, d['alpha'], phi,
            d['delta'], k, c, g, 2.1, 1.5)
        pl, pe, pa, audit = functions['refresh_alpha_gauge'](lam, d['eta'], d['alpha'], rng, d['s'], 'synthetic')
        result = dict(Yhat=yhat, qgk=q, Lambda=lam, updated_Yhat=updated_yhat,
                      sigma2=sigma2, phi=phi, delta=delta, tau=tau,
                      px_loading=pl, px_eta=pe, px_alpha=pa, px_audit=audit,
                      global_rng_sha256=rng_hash(np.random.get_state()),
                      px_rng_state=copy.deepcopy(rng.bit_generator.state))
        for name in d:
            np.testing.assert_array_equal(d[name], before[name])
        return serial(result)
    finally:
        np.random.set_state(saved_rng)


def create_fixture(root):
    reference, identities = historical_functions(root)
    cases = []
    with threadpool_limits(limits=1):
        for counts, g, k, seed, order in [([5], 3, 1, 9, 'C'),
                ([2, 4, 6], 4, 2, 41, 'C'), ([2, 4, 6], 3, 4, 20261027, 'F')]:
            rng = np.random.default_rng(seed+17); c = len(counts); n = sum(counts)
            delta = rng.uniform(.7, 1.3, k)
            inputs = serial(dict(counts=counts, Y=rng.normal(size=(g, n)),
                loading=rng.normal(size=(c, g, k)), eta=rng.normal(size=(k, n)),
                alpha=rng.uniform(.3, 1.5, k), sigma2=rng.uniform(.2, 1.2, g),
                phi=rng.uniform(.6, 1.5, (g, k)), delta=delta, tau=np.cumprod(delta),
                s=np.full(k, .20)))
            expected = evaluate(reference, inputs, seed, order)
            actual = evaluate(port_functions(), inputs, seed, order)
            # Full float64 JSON roundtrip preserves bits. No tolerance allowance.
            if actual != expected:
                raise AssertionError('Exact source/port outputs or RNG states differ')
            cases.append(dict(seed=seed, order=order, inputs=inputs, expected=expected))
        return dict(schema='bsfm.sampler-layer1-regression.v1', sources=identities,
                    environment=dict(python=platform.python_version(), numpy=np.__version__,
                                     scipy=scipy.__version__, platform=platform.platform(),
                                     threads=1, libraries=threadpool_info()),
                    comparison='exact outputs and post-call RNG states; no tolerance amendment', cases=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = create_fixture(args.source_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('PASS: three exact historical/port fixtures, seven functions, both RNG streams; no refit.')
