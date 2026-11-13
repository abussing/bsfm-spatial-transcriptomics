"""Run two frozen GPU recipes through the normal launcher and test non-replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import traceback

ROOT = Path(__file__).resolve().parents[2]


def record(path):
    path = Path(path)
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size, sha256=hashlib.file_digest(stream,'sha256').hexdigest())


def inventory(root):
    return {p.relative_to(root).as_posix():record(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--commit', required=True)
    p.add_argument('--recipes', type=Path, required=True)
    p.add_argument('--recipes-sha256', required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('External validation output required')
    output.mkdir(parents=True, exist_ok=False)
    report = dict(schema='bsfm.gpu-cli-validation.v1', status='FAIL',
                  source_commit=args.commit, recipes_sha256=args.recipes_sha256,
                  models={}, scientific_result=False)
    try:
        if (subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip() != args.commit
                or subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()):
            raise ValueError('Clean exact source required')
        if Path(os.environ['BSFM_CHECKOUT']).resolve() != ROOT:
            raise ValueError('Launcher checkout differs from validator')
        if record(args.recipes)['sha256'] != args.recipes_sha256:
            raise ValueError('Validation recipes manifest changed')
        manifest = json.loads(args.recipes.read_text())
        if manifest['schema'] != 'bsfm.cli-validation-inputs.v1' or set(manifest['recipes']) != {'deep','flat'}:
            raise ValueError('Pinned deep and learned-range flat recipes required')
        # Slurm executes spooled scripts; exercise the same path behavior here.
        launcher = output/'sample.sbatch'
        shutil.copyfile(ROOT/'environment/hpc/sample.sbatch', launcher)
        report['launcher'] = record(launcher)
        for model in ('deep','flat'):
            pin = manifest['recipes'][model]
            recipe = (args.recipes.resolve().parent/pin['path']).resolve()
            if record(recipe) != {k:pin[k] for k in ('bytes','sha256')}:
                raise ValueError('Frozen recipe changed')
            settings = json.loads(recipe.read_text())
            if (settings['backend'] != 'gpu' or settings['model'] != model
                    or (model == 'flat' and 'flat_range_prior' not in settings)):
                raise ValueError('GPU deep/learned-range flat comparison required')
            command = ['bash',str(launcher),args.commit,str(recipe),str(output/model)]
            row = dict(command=command, recipe=record(recipe)); report['models'][model] = row
            for label in ('initial','completed-restart'):
                print(model, label, flush=True)
                log = output/f'{model}-{label}.log'
                with log.open('wb') as stream:
                    subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
                row[label+'_log'] = record(log)
                text = log.read_text()
                completion = json.loads(text.strip().splitlines()[-1])
                if (completion['schema'] != 'bsfm.recipe-completion.v1'
                        or completion['production_run_id'] != settings['phases'][-1]['run_id']
                        or [x['result']['completed'] for x in completion['phases']]
                        != [x['sweeps'] for x in settings['phases']]):
                    raise ValueError('Unexpected phase completion')
                for phase, result in zip(settings['phases'],completion['phases']):
                    expected = len({1,phase['sweeps'],*range(phase['save_every'],phase['sweeps']+1,phase['save_every'])})
                    if result['result']['retained'] != expected:
                        raise ValueError('Retained draw cadence differs from recipe')
                current = inventory(output/model)
                if label == 'initial':
                    before = current; row['completion'] = completion
                elif (current != before or completion != row['completion']
                      or any(line.startswith(('SWEEP ','FACTOR WARMUP BEGIN')) for line in text.splitlines())):
                    raise ValueError('Completed restart replayed work or changed saved output')
            row.update(completed_nonreplay=True, output_inventory=before)
        report['status'] = 'PASS'
    except BaseException:
        report['error'] = traceback.format_exc()
        raise
    finally:
        (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps(dict(status=report['status'],scientific_result=False)),flush=True)


if __name__ == '__main__':
    main()
