"""Materialize only the external, locked mesh environment (not the study harness)."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

from acquire import identity, fetch


def write_csv(path, rows):
    with path.open('w',encoding='utf-8',newline='') as out:
        writer=csv.DictWriter(out,fieldnames=list(rows[0]),lineterminator='\n')
        writer.writeheader();writer.writerows(rows)


def runtime_tree(home):
    rows=[dict(relative=p.relative_to(home).as_posix(), **identity(p))
          for p in sorted(home.rglob('*')) if p.is_file()]
    value=''.join(f"{r['relative']}\t{r['bytes']}\t{r['sha256']}\n" for r in rows)
    return dict(root=str(home),files=rows,sha256=hashlib.sha256(value.encode()).hexdigest())


def main():
    ap=argparse.ArgumentParser();ap.add_argument('root',type=Path)
    ap.add_argument('--r',action='store_true');ap.add_argument('--python',action='store_true')
    ap.add_argument('--offline',action='store_true')
    args=ap.parse_args();root=args.root.resolve()
    if args.r:
        lock=json.loads((root/'r-source-lock.json').read_text(encoding='utf-8'))
        rs=Path(lock['runtime']['path']);assert identity(rs)==lock['runtime']
        home=rs.parents[2]
        before=runtime_tree(home)
        prior=root/'immutable-runtime-before.json'
        if prior.exists():assert json.loads(prior.read_text(encoding='utf-8'))['sha256']==before['sha256']
        else:prior.write_text(json.dumps(before,indent=2)+'\n')
        packages={p['package']:p for p in lock['packages']}
        versions={k:v['Version'] for k,v in lock['base_packages'].items()}
        versions.update({k:v['version'] for k,v in packages.items()});versions['R']='4.5.3'
        constraints=[];deps={}
        for name,p in packages.items():
            for kind in ['source','binary']:
                actual=identity(Path(p[kind]['path']))
                assert all(actual[k]==p[kind][k] for k in ['bytes','sha256','path'])
            ds=set()
            for description in [p['source_description'],p['description']]:
                for key in ['Depends','Imports','LinkingTo']:
                    for item in description.get(key,'').split(','):
                        item=item.strip()
                        if not item:continue
                        m=re.fullmatch(r'([A-Za-z][A-Za-z0-9.]*)\s*(?:\(([><=]+)\s*([^)]+)\))?',item)
                        if not m:raise ValueError(item)
                        dep,op,ver=m.groups();assert dep in versions,(name,dep)
                        if dep in packages:ds.add(dep)
                        if op:constraints.append(dict(package=name,dependency=dep,operator=op,required=ver,actual=versions[dep]))
            deps[name]=ds
        order=[]
        while len(order)<len(packages):
            ready=sorted(n for n,d in deps.items() if n not in order and d<=set(order))
            if not ready:raise ValueError('Dependency cycle')
            order.extend(ready)
        write_csv(root/'install-plan.csv',[dict(package=n,version=versions[n],binary=packages[n]['binary']['path']) for n in order])
        write_csv(root/'dependency-constraints.csv',constraints)
        command=[str(rs),'--vanilla',str(Path(__file__).with_name('install.R').resolve()),str(root)]
        env=os.environ.copy();env.update(TMPDIR=str(root/'tmp'),TEMP=str(root/'tmp'),TMP=str(root/'tmp'),LANG='C',LC_ALL='C')
        (root/'tmp').mkdir(exist_ok=True)
        with (root/'r-install.log').open('w') as out:
            result=subprocess.run(command,env=env,stdout=out,stderr=subprocess.STDOUT)
        (root/'r-install-command.json').write_text(json.dumps(dict(command=command,returncode=result.returncode),indent=2)+'\n')
        assert result.returncode==0,(root/'r-install.log')
        after=runtime_tree(home);assert after['sha256']==before['sha256']
        (root/'immutable-runtime-after.json').write_text(json.dumps(dict(root=str(home),sha256=after['sha256'],files=len(after['files']),unchanged=True),indent=2)+'\n')
        print('R installation passed:',len(order),'packages;',len(constraints),'dependency constraints; immutable runtime unchanged')
    if args.python:
        prior_lock=root/'python-source-lock.json'
        if prior_lock.exists():
            prior=json.loads(prior_lock.read_text(encoding='utf-8'))
            installs=[dict(metadata=dict(name=w['package'],version=w['version']),
                download_info=dict(url=w['url'],archive_info=dict(hashes=dict(sha256=w['sha256']))))
                for w in prior['wheels']]
        else:
            if args.offline:
                raise FileNotFoundError('Offline build requires python-source-lock.json')
            installs=json.loads((root/'python-resolution.json').read_text(encoding='utf-8'))['install']
        lines=[];wheels=[]
        for row in installs:
            name=row['metadata']['name'];version=row['metadata']['version'];url=row['download_info']['url']
            wanted=row['download_info']['archive_info']['hashes']['sha256']
            target=root/'downloads/wheels'/url.rsplit('/',1)[-1]
            if args.offline and not target.is_file():
                raise FileNotFoundError(f'Offline build requires cached wheel: {target}')
            record=dict(url=url,**identity(target)) if target.exists() else fetch(url,target)
            assert record['sha256']==wanted
            wheels.append(dict(package=name,version=version,**record))
            lines.append(f'{name}=={version} --hash=sha256:{wanted}')
        requirements=root/'python-requirements.lock.txt';requirements.write_text('\n'.join(sorted(lines))+'\n')
        py=root/'python/Scripts/python.exe'
        command=[str(py),'-B','-m','pip','--isolated','--disable-pip-version-check','install','--no-index','--no-cache-dir','--find-links',str(root/'downloads/wheels'),'--require-hashes','-r',str(requirements)]
        result=subprocess.run(command,capture_output=True,text=True)
        (root/'python-install.log').write_text(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr
        check=subprocess.run([str(py),'-B','-m','pip','check'],capture_output=True,text=True);assert check.returncode==0,check.stdout
        freeze=subprocess.check_output([str(py),'-B','-m','pip','freeze','--all'],text=True)
        (root/'python-freeze.txt').write_text(freeze)
        (root/'python-source-lock.json').write_text(json.dumps(dict(schema_version=1,python=identity(py),wheels=wheels,command=command,pip_check=check.stdout),indent=2)+'\n')
        print('Python installation passed',freeze)


if __name__=='__main__':main()
