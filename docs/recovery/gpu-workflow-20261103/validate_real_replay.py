"""Real-size diagnostic sweeps from authenticated old input, under a new contract.

This deliberately seeds a diagnostic experiment from prior adapted values; it
does not migrate a scientific chain or claim the new code generated old warmup.
"""
import argparse, copy, json, os, shutil, subprocess, sys, time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--commit', required=True)
p.add_argument('--output', type=Path, required=True)
p.add_argument('--worker', choices=['strict', 'incremental', 'interrupt', 'resume', 'nonreplay'])
a = p.parse_args()
repo = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(repo/'src'), str(repo/'docs/holdouts/s10-grid-20261103')]
from experiment import clean, target_and_seeds, use_incremental_store
from gpu_run import authenticate_gpu_environment
from bsfm.sampler.run_controller import RunController
from bsfm.sampler.run_genesis import load_genesis
from bsfm.sampler.run_storage import read_json, file_record
from bsfm.sampler.checkpoint_contract import digest

source = Path('/work/abussing/bsfm-consolidation/evidence/real-timing-22015787/threads-1/strict')
genesis = source/'segments/segment/genesis/endpoint.npz'
prepared = Path('/work/abussing/bsfm-consolidation/evidence/holey-27f9b3f0dfa4c1df2acc9e845633a8031069daea/circles12_diameter1of8/prepared')


def make(root, incremental):
    clean(a.commit)
    runtime = authenticate_gpu_environment()
    target, loading, eta, receipt = target_and_seeds(prepared, 'deep', genesis)
    binding = read_json(source/'input-receipt.json')
    old_spec = read_json(source/'run-spec.json')
    old = RunController(root/'unused', target, loading, eta, old_spec, binding,
                        authenticate=target._validate_identities)
    endpoint, _ = load_genesis(genesis, target, old.cp)
    spec = copy.deepcopy(old_spec)
    spec.update(run_id='fixed_gradient_diagnostic', production_sweeps=3, final_sweep=3)
    spec['software'] = dict(git_commit=a.commit, clean_tree=True,
        environment_identity=digest(runtime), environment_lock_sha256=runtime['lock']['sha256'],
        run_config_sha256=digest(dict(scope='diagnostic_seed_not_scientific_resume',
            source_genesis=file_record(genesis), source_software=old_spec['software'], sweeps=3)))

    def auth():
        clean(a.commit)
        target._validate_identities()
        if authenticate_gpu_environment() != runtime:
            raise ValueError('Runtime changed')
        if read_json(prepared/'prepared.json') != receipt:
            raise ValueError('Preparation receipt changed')
        for name, record in receipt['files'].items():
            if file_record(prepared/name) != record:
                raise ValueError('Prepared file changed')

    class DiagnosticController(RunController):
        def _adapt_endpoint(self, fault):
            # The diagnostic contract identifies both old seed and new code.
            return copy.deepcopy(endpoint)

    c = DiagnosticController(root, target, loading, eta, spec, binding, authenticate=auth)
    if incremental:
        use_incremental_store(c)
    return c, runtime


if a.worker:
    root = a.output / (a.worker if a.worker in ('strict', 'incremental') else 'restart')
    c, runtime = make(root, a.worker != 'strict')
    start = time.monotonic()
    events = []
    def event(stage):
        events.append(dict(stage=stage, seconds=time.monotonic()-start))
        if stage in ('before_sweep', 'after_sweep', 'after_transaction_publish'):
            print('REPLAY', a.worker, stage, round(time.monotonic()-start, 3), flush=True)
        if a.worker == 'interrupt' and stage == 'after_checkpoint_candidate':
            os._exit(91)
    if a.worker == 'nonreplay':
        def no_sweep(*args, **kwargs):
            raise AssertionError('Committed sweep replayed')
        c.layer.sweep = no_sweep
    result = c.run(fault=event)
    (a.output/(a.worker+'.json')).write_text(json.dumps(dict(
        completion=result, environment=runtime, seconds=time.monotonic()-start, events=events), indent=2)+'\n')
    sys.exit(0)

a.output.mkdir(parents=True, exist_ok=False)
receipt = dict(status='INCOMPLETE', commit=a.commit,
    scope='Three real K12/L14 sweeps per arm, diagnostic seed, no new warmup or scientific fit',
    source_genesis=dict(path=str(genesis), **file_record(genesis)), checks=[])

def worker(name, expected=0):
    result = subprocess.run([sys.executable, '-u', str(Path(__file__).resolve()),
        '--commit', a.commit, '--output', str(a.output), '--worker', name])
    if result.returncode != expected:
        raise AssertionError((name, result.returncode, expected))
    if expected == 0:
        receipt[name] = read_json(a.output/(name+'.json'))
    (a.output/'validation.json').write_text(json.dumps(receipt, indent=2)+'\n')

def compare(left, right):
    for n in range(1, 4):
        rel = Path('segments/segment/transactions')/f'{n:012d}'/'prepared.json'
        if read_json(a.output/left/rel) != read_json(a.output/right/rel):
            raise AssertionError(f'Transaction mismatch: {left}/{right} sweep {n}')
    receipt['checks'].append(dict(left=left, right=right, three_transactions_exact=True))

try:
    worker('strict')
    worker('incremental')
    compare('strict', 'incremental')
    src = a.output/'incremental'
    restart = a.output/'restart'
    restart.mkdir()
    for name in ['run-spec.json', 'input-receipt.json']:
        shutil.copyfile(src/name, restart/name)
    seg = restart/'segments/segment'
    seg.mkdir(parents=True)
    shutil.copytree(src/'segments/segment/genesis', seg/'genesis')
    (seg/'transactions').mkdir()
    shutil.copytree(src/'segments/segment/transactions/000000000001',
                    seg/'transactions/000000000001')
    worker('interrupt', 91)
    worker('resume')
    compare('incremental', 'restart')
    worker('nonreplay')
    receipt['checks'].append(dict(completed_nonreplay=True, fresh_process_uncommitted_recomputation=True))
    receipt['status'] = 'PASS'
except BaseException as exc:
    receipt.update(status='FAIL', error=repr(exc))
    raise
finally:
    (a.output/'validation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print('REAL_REPLAY_GATE', receipt['status'], flush=True)
