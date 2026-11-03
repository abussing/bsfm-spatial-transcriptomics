"""Same-runtime Layer-4 reference and chart-boundary checks; no fixture edits."""
import copy
from dataclasses import replace
import json
from pathlib import Path
import sys
import jax
import jax.numpy as jnp
import numpy as np
from scipy.special import logit
from sampler_layer4_support import historical, evaluate
from sampler_layer6_support import fixture_system
from bsfm.sampler.chart import validate_chart_state


def main(output):
    report = {'status': 'incomplete', 'layer4': [], 'chart': []}
    output = Path(output)
    def save():
        output.write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')
    save()
    reference, sources = historical('/work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/code/sampler')
    report['sources'] = sources
    for seed in (12, 37):
        original, port = evaluate(seed, reference), evaluate(seed)
        report['layer4'].append({'seed': seed, 'source_port_exact': original == port})
        save()
        if original != port:
            raise RuntimeError('Layer-4 source/port mismatch in same runtime')
    target, state, positions, _, _, _ = fixture_system()
    for i, p in enumerate(positions):
        validate_chart_state(target, p, state, i)
    p = positions[0]
    for name, direction in [('alpha', np.inf), ('zeta', -np.inf)]:
        changed = copy.deepcopy(state)
        a = getattr(changed, name)
        a[0] = np.nextafter(a[0], direction)
        try:
            validate_chart_state(target, p, changed, 0)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed physical parameter accepted')
    for coordinate, direction in [(0, -np.inf), (1, np.inf)]:
        a = p.values.copy()
        decisions = []
        for step in range(1, 9):
            a[coordinate] = np.nextafter(a[coordinate], direction)
            expected = (a[0] == np.log(state.alpha[0]) or state.alpha[0] == float(np.exp(a[0]))) if coordinate == 0 else (
                a[1] == logit(state.zeta[0]) or state.zeta[0] == float(jax.nn.sigmoid(jnp.asarray(a[1]))))
            try:
                validate_chart_state(target, replace(p, values=a.copy()), state, 0)
                accepted = True
            except ValueError:
                accepted = False
            decisions.append({'ulp_steps': step, 'expected': bool(expected), 'accepted': accepted})
            if accepted != expected:
                raise AssertionError('Chart validation differs from exact forward/inverse contract')
        if all(r['accepted'] for r in decisions):
            raise AssertionError('No rejection boundary found in bounded chart probe')
        report['chart'].append({'coordinate': coordinate, 'decisions': decisions})
        save()
    report['status'] = 'pass'
    report['scope'] = 'Same-runtime source equality and exact chart contract; no Windows fixture waiver or scientific fit'
    save()


if __name__ == '__main__':
    main(sys.argv[1])
