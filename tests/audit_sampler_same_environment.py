"""Explicit source-authenticated runtime references, then the full sampler suite.

Default unittest discovery continues to compare with the committed Windows
fixtures. This separately invoked audit uses the same frozen synthetic inputs
but evaluates authenticated original functions on this machine. No fixture on
disk, sampler formula, tolerance, RNG interface or test assertion is changed.
"""
import argparse
import copy
import hashlib
import importlib
import importlib.metadata
import json
import platform
import sys
import traceback
import unittest
from pathlib import Path

import jax
import numpy as np
from threadpoolctl import threadpool_info, threadpool_limits

from build_sampler_layer1_fixture import historical_functions, evaluate as eval1, port_functions as port1
from sampler_layer2_support import historical_reference, synthetic, evaluate as eval2, port_functions as port2, serial
from sampler_layer3_support import historical, system, evaluate as eval3

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--code-commit', required=True)
    args = parser.parse_args()
    if len(args.code_commit) != 40 or any(c not in '0123456789abcdef' for c in args.code_commit):
        parser.error('An exact lowercase Git commit SHA is required')
    if not jax.config.x64_enabled or jax.default_backend() != 'cpu':
        parser.error('This bounded audit requires CPU and JAX x64')
    args.output.mkdir(parents=True, exist_ok=False)
    report = dict(schema='bsfm.same-environment-sampler-audit.v1', status='INCOMPLETE',
                  code_commit=args.code_commit, source_root=str(args.source_root),
                  fixture_policy='Unchanged committed inputs; independently authenticated original-function outputs; exact equality',
                  comparisons=[], test_result=None)
    fixtures = [ROOT/f'tests/fixtures/sampler_layer{i}.json' for i in (1, 2, 3)]
    report['committed_fixture_sha256'] = {p.name: sha(p) for p in fixtures}
    modules = [importlib.import_module(f'test_sampler_layer{i}') for i in (1, 2, 3)]
    original = [m.FIXTURE for m in modules]
    runtime = [copy.deepcopy(f) for f in original]
    try:
        # Authenticate every required historical source before any suite override.
        ref1, sources1 = historical_functions(args.source_root)
        ref2, sources2 = historical_reference(args.source_root)
        ref3, sources3 = historical(args.source_root)
        report['reference_sources'] = [sources1, sources2, sources3]
        report['environment'] = dict(python=sys.version, platform=platform.platform(),
            packages={p: importlib.metadata.version(p) for p in
                      ('numpy', 'scipy', 'jax', 'jaxlib', 'ml_dtypes', 'opt_einsum', 'threadpoolctl')},
            backend=jax.default_backend(), x64=jax.config.x64_enabled)

        def compare(layer, index, expected, actual):
            exact = expected == actual
            report['comparisons'].append(dict(layer=layer, case=index, source_port_exact=exact,
                windows_fixture_exact=expected == original[layer-1]['cases'][index]['expected']))
            if not exact:
                raise AssertionError(f'Layer {layer} case {index}: source/port or RNG outputs differ')
            # Only the expectation changes in this explicitly selected audit.
            # Sources, inputs, seeds, order and all test assertions stay intact.
            runtime[layer-1]['cases'][index]['expected'] = expected

        with threadpool_limits(limits=1):
            report['environment']['numerical_libraries'] = threadpool_info()
            for i, case in enumerate(original[0]['cases']):
                values = (case['inputs'], case['seed'], case['order'])
                compare(1, i, eval1(ref1, *values), eval1(port1(), *values))
            for i, case in enumerate(original[1]['cases']):
                values = (synthetic(case['scale']), float(np.log(case['ell'])))
                compare(2, i, serial(eval2(ref2, *values)), serial(eval2(port2(), *values)))
            for i, case in enumerate(original[2]['cases']):
                values = system(case['seed'])
                compare(3, i, eval3(*values, ref3), eval3(*values))

            for i, (module, fixture) in enumerate(zip(modules, runtime), 1):
                # Original source metadata stays available to provenance tests.
                # Actual runtime source locations/hashes are recorded above.
                (args.output/f'layer{i}-runtime-reference.json').write_text(
                    json.dumps(fixture, indent=2, allow_nan=False)+'\n', encoding='utf-8')
                module.FIXTURE = fixture
            suite = unittest.TestSuite()
            for module in modules + [importlib.import_module('test_sampler_provenance')]:
                suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
            result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
            report['test_result'] = dict(run=result.testsRun,
                failures=[str(t) for t, _ in result.failures], errors=[str(t) for t, _ in result.errors],
                skips=[str(t) for t, _ in result.skipped], successful=result.wasSuccessful())
            if result.testsRun != 75 or not result.wasSuccessful() or result.skipped:
                raise AssertionError('Expected 70 original sampler plus 5 provenance tests, all passing with no skips')
        report['status'] = 'PASS'
    except Exception:
        report['status'] = 'FAIL'
        report['exception'] = traceback.format_exc()
        traceback.print_exc()
    finally:
        for module, fixture in zip(modules, original):
            module.FIXTURE = fixture
        unchanged = {p.name: sha(p) for p in fixtures} == report['committed_fixture_sha256']
        report['committed_fixtures_unchanged'] = unchanged
        if not unchanged:
            report['status'] = 'FAIL'
        report['runtime_reference_sha256'] = {
            p.name: sha(p) for p in sorted(args.output.glob('layer*-runtime-reference.json'))}
        (args.output/'report.json').write_text(
            json.dumps(report, indent=2, allow_nan=False)+'\n', encoding='utf-8')
    print('AUDIT_STATUS='+report['status'])
    return 0 if report['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
