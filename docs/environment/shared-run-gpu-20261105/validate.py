"""Bounded actual-CLI GPU check; standard library only in the supervising process."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import traceback


def record(path):
    with path.open('rb') as stream:
        return dict(bytes=path.stat().st_size,sha256=hashlib.file_digest(stream,'sha256').hexdigest())


def inventory(root):
    return {p.relative_to(root).as_posix():record(p) for p in sorted(root.rglob('*')) if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();repo=Path(__file__).resolve().parents[3]
    output=args.output.resolve();output.mkdir(parents=True,exist_ok=False)
    report=dict(status='RUNNING',commit=args.commit,models={},scientific_result=False)
    try:
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()!=args.commit:
            raise ValueError('Wrong checkout')
        receipt=json.loads(Path(__file__).with_name('FIXTURE_INVENTORY.json').read_text())
        fixture=Path(receipt['hpc_root'])
        expected={r['path']:{k:r[k] for k in ('bytes','sha256')} for r in receipt['files']}
        if inventory(fixture)!=expected:raise ValueError('Synthetic fixture inventory mismatch')
        report['fixture_inventory_sha256']=record(Path(__file__).with_name('FIXTURE_INVENTORY.json'))['sha256']
        for model in ('deep','flat'):
            command=[sys.executable,'-B','-m','bsfm.sampler.run','--recipe',
                str(repo/f'config/sampler/shared-command-gpu-{model}-validation.json'),
                '--output',str(output/model),'--commit',args.commit]
            row=dict(command=command);report['models'][model]=row
            for label in ('initial','completed-restart'):
                log=output/f'{model}-{label}.log'
                with log.open('wb') as stream:
                    subprocess.run(command,cwd=repo,stdout=stream,stderr=subprocess.STDOUT,check=True)
                row[label+'_log']=record(log)
                text=log.read_text()
                if label=='completed-restart' and any(line.startswith(('SWEEP ','FACTOR WARMUP BEGIN')) for line in text.splitlines()):
                    raise ValueError('Completed restart executed transitions or tuning')
                completion=json.loads(text.strip().splitlines()[-1])
                if ([x['result']['completed'] for x in completion['phases']]!=[1,2]
                    or [x['result']['retained'] for x in completion['phases']]!=[1,2]
                    or completion['production_run_id']!='production'):
                    raise ValueError('Unexpected phase completion')
                current=inventory(output/model)
                if label=='initial':
                    before=current;row['completion']=completion
                elif current!=before or completion!=row['completion']:
                    raise ValueError('Completed command changed its output inventory')
            row['completed_nonreplay']=True;row['output_inventory']=before
        report['status']='PASS'
    except BaseException:
        report['status']='FAIL';report['error']=traceback.format_exc();raise
    finally:
        (output/'validation.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
