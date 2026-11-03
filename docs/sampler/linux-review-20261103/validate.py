"""Stage receipts survive failure/timeout; no scientific data is opened."""
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time
import traceback
import unittest

repo = Path(__file__).resolve().parents[3]
commit, job = sys.argv[1:3]
mode = sys.argv[3] if len(sys.argv) == 4 else 'full'
assert mode in ('full', 'storage')
assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == commit
assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
assert job.isdigit()
root = Path('/work/abussing/bsfm-consolidation/evidence') / ('layer9-linux-' + job)
root.mkdir(exist_ok=False)
(root/'tmp').mkdir()
tempfile.tempdir = str(root/'tmp')
os.environ['TMPDIR'] = str(root/'tmp')
os.environ['BSFM_LAYER9_ARTIFACTS'] = str(root/'synthetic')
os.environ['BSFM_LAYER9_RECEIPT'] = str(root/'synthetic-receipt.json')


def inventory():
    paths = sorted(list((repo/'src').rglob('*.py')) + list((repo/'tests').rglob('*')))
    return {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}


def save(name, data):
    (root/(name+'.json')).write_text(json.dumps(data, indent=2, allow_nan=False)+'\n')


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite): yield from flatten(item)
        else: yield item


def run_stage(name, pattern, exclude_layer9=False):
    start = time.monotonic()
    suite = unittest.defaultTestLoader.discover(str(repo/'tests'), pattern=pattern)
    if exclude_layer9:
        suite = unittest.TestSuite(t for t in flatten(suite) if not t.__class__.__module__.startswith('test_sampler_layer9'))
    with (root/(name+'.log')).open('w', buffering=1) as stream:
        result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = dict(status='pass' if result.wasSuccessful() else 'not_passed',
                  tests_run=result.testsRun, failures=[(str(t), e) for t,e in result.failures],
                  errors=[(str(t), e) for t,e in result.errors], skipped=[(str(t), e) for t,e in result.skipped],
                  seconds=time.monotonic()-start)
    save(name, report)
    print(name, report['status'], report['tests_run'], flush=True)
    return report


before = inventory()
report = dict(status='incomplete', commit=commit, job_id=job, platform=platform.platform(),
              scope='Synthetic CPU only', mode=mode, stages={}, source_inventory=before)
save('validation', report)
try:
    from bsfm.sampler.run_inputs import authenticate_environment
    save('environment-authentication', authenticate_environment())
    report['stages']['storage'] = run_stage('storage', 'test_sampler_layer9_portability.py')
    if report['stages']['storage']['status'] != 'pass':
        raise RuntimeError('Storage gate failed; numerical stages not started')
    if mode == 'full':
        report['stages']['layer9'] = run_stage('layer9', 'test_sampler_layer9*.py')
        save('validation', report)
        report['stages']['accepted'] = run_stage('accepted', 'test_sampler*.py', exclude_layer9=True)
        save('validation', report)
        report['stages']['mesh'] = run_stage('mesh', 'test_mesh*.py')
    report['source_unchanged'] = before == inventory()
    report['status'] = 'pass' if report['source_unchanged'] and all(s['status']=='pass' for s in report['stages'].values()) else 'not_passed'
except BaseException:
    report['exception'] = traceback.format_exc()
    report['status'] = 'not_passed'
    raise
finally:
    save('validation', report)
sys.exit(0 if report['status']=='pass' else 1)
