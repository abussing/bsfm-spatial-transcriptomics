"""Independent same-runtime historical comparisons; never rewrite fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

repo = Path(__file__).resolve().parents[3]
commit, job = sys.argv[1:]
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == commit
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
assert job.isdigit()
root = Path('/work/abussing/bsfm-consolidation/evidence')/('layer9-reference-'+job)
root.mkdir(exist_ok=False)
source = Path('/work/abussing/bsfm-consolidation/reviews/layer9-portability-20261103/payload/evidence')


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


fixtures = {str(p.relative_to(repo)): sha(p) for p in (repo/'tests/fixtures').glob('sampler_layer*.json')}
start = time.monotonic()
report = dict(status='incomplete', commit=commit, job_id=job,
              scope='Synthetic same-runtime reference comparisons; frozen fixtures remain unchanged',
              fixture_inventory=fixtures, comparisons={})


def save():
    (root/'report.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


save()
try:
    from bsfm.sampler.run_inputs import authenticate_environment
    report['environment'] = authenticate_environment()
    save()
    with (root/'layers123.log').open('w') as stream:
        result = subprocess.run([sys.executable, '-B', str(repo/'tests/audit_sampler_same_environment.py'),
                                 '--source-root', str(source), '--output', str(root/'layers123'),
                                 '--code-commit', commit], stdout=stream, stderr=subprocess.STDOUT)
    report['comparisons']['layers123'] = dict(exit_code=result.returncode,
        receipt_sha256=sha(root/'layers123/report.json'))
    save()
    from threadpoolctl import threadpool_limits
    from sampler_layer5_support import historical, evaluate
    from sampler_layer6_support import authenticated_literal, run_case
    for layer in (5, 6):
        before = time.monotonic()
        if layer == 5:
            reference, identities = historical(source)
            with threadpool_limits(limits=1):
                original = evaluate(reference); actual = evaluate()
        else:
            reference, identities = authenticated_literal(source)
            with threadpool_limits(limits=1):
                original = run_case(reference); actual = run_case()
        fixture = json.loads((repo/f'tests/fixtures/sampler_layer{layer}.json').read_text())['expected']
        row = dict(same_environment_source_port_exact=original==actual,
                   saved_windows_fixture_exact=fixture==actual, sources=identities,
                   elapsed_seconds=time.monotonic()-before)
        report['comparisons'][str(layer)] = row
        (root/f'layer{layer}-values.json').write_text(json.dumps(dict(original=original,port=actual),indent=2,allow_nan=False)+'\n')
        save()
        print('layer',layer,row['same_environment_source_port_exact'],flush=True)
    report['fixtures_unchanged'] = all(sha(repo/p)==h for p,h in fixtures.items())
    report['status'] = 'pass' if (result.returncode==0 and report['fixtures_unchanged']
        and all(report['comparisons'][str(i)]['same_environment_source_port_exact'] for i in (5,6))) else 'not_passed'
finally:
    report['elapsed_seconds'] = time.monotonic()-start
    save()
sys.exit(0 if report['status']=='pass' else 1)
