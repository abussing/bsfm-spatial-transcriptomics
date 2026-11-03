"""Real-input gradient and split-transition gate, no repeated adaptation."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

p = argparse.ArgumentParser()
p.add_argument('--commit', required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=False)
receipt = dict(status='INCOMPLETE', commit=a.commit,
    scope='Real K12/L14 saved-input gradient and first split transition; no warmup or scientific fitting')
try:
    for name, script in [('gradient', 'diagnose_gradient.py'), ('transition', 'diagnose_transition.py')]:
        subprocess.run([sys.executable, '-u', str(Path(__file__).with_name(script)),
            '--commit', a.commit, '--output', str(a.output/name)], check=True)
        receipt[name] = json.loads((a.output/name/'diagnostic.json').read_text())
    assert receipt['gradient']['full_value_gradient']['all_exact'], 'Full gradient not repeatable'
    errors = receipt['gradient']['analytic_vs_autodiff']
    assert errors['relative_value_error'] <= 2e-12, 'Independent value mismatch'
    assert errors['relative_gradient_error'] <= 2e-10, 'Independent gradient mismatch'
    for name in ['same_runner_repeat', 'new_runner']:
        assert receipt['transition'][name]['comparison']['exact'], 'Split transition not repeatable: '+name
    receipt['status'] = 'PASS'
except BaseException as exc:
    receipt.update(status='FAIL', error=repr(exc))
    raise
finally:
    (a.output/'validation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('ACCUMULATION_GATE', receipt['status'], flush=True)
