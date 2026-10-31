"""Rehydrate the reviewed locks in a fresh root, without version resolution."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from acquire import identity, fetch
from build import runtime_tree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    ap.add_argument('--rscript', type=Path, required=True)
    ap.add_argument('--python-base', type=Path, required=True)
    ap.add_argument('--offline', action='store_true', help='Require cached authenticated archives; never fetch')
    args = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = args.root.resolve()
    if root.exists():
        raise ValueError('Restoration requires a completely new environment root')
    if root.is_relative_to(here.parents[1]):
        raise ValueError('Environment must remain outside the repository')
    rlock = json.loads((here/'r-source-lock.json').read_text(encoding='utf-8'))
    pylock = json.loads((here/'python-source-lock.json').read_text(encoding='utf-8'))
    runtime = json.loads((here/'runtime-lock.json').read_text(encoding='utf-8'))
    package_lock = json.loads((here/'r-packages.lock.json').read_text(encoding='utf-8'))
    assert {p['package']:p['version'] for p in rlock['packages']} == {k:v['version'] for k,v in package_lock['packages'].items()}
    for p in rlock['packages']:
        for kind in ['source','binary']:
            assert p[kind]['sha256'] == package_lock['packages'][p['package']][kind+'_sha256']
    expected_requirements = '\n'.join(sorted(f"{w['package']}=={w['version']} --hash=sha256:{w['sha256']}" for w in pylock['wheels']))+'\n'
    assert (here/'python-requirements.lock.txt').read_text(encoding='utf-8') == expected_requirements
    if args.offline:
        for record in [p[k] for p in rlock['packages'] for k in ['source','binary']] + pylock['wheels']:
            cached = identity(Path(record['path']))  # Missing archive fails before creating a root.
            assert all(cached[k] == record[k] for k in ['bytes','sha256'])
    assert identity(args.rscript)['sha256'] == rlock['runtime']['sha256']
    assert runtime_tree(args.rscript.resolve().parents[2])['sha256'] == runtime['R_tree']['sha256']
    assert identity(args.python_base)['sha256'] == runtime['python_base']['sha256']
    for original in runtime['python_base_companions']:
        assert identity(args.python_base.parent/Path(original['path']).name)['sha256'] == original['sha256']
    pip_wheel = args.python_base.parent/'Lib/ensurepip/_bundled'/Path(runtime['pip_bootstrap']['path']).name
    assert identity(pip_wheel)['sha256'] == runtime['pip_bootstrap']['sha256']
    assert subprocess.check_output([str(args.python_base),'-B','-c','import platform; print(platform.python_version())'],text=True).strip() == '3.12.0'
    root.mkdir(parents=True)
    def acquire_locked(record, folder):
        original = Path(record['path'])
        target = root/'downloads'/folder/original.name
        target.parent.mkdir(parents=True,exist_ok=True)
        if original.exists():
            assert identity(original)['sha256'] == record['sha256']
            shutil.copyfile(original,target)
        else:
            if args.offline:
                raise FileNotFoundError(f'Offline restoration requires cached archive: {original}')
            fetch(record['url'],target)
        actual = identity(target)
        assert all(actual[k] == record[k] for k in ['bytes','sha256'])
        return dict(url=record['url'],**actual)
    rlock['runtime'] = identity(args.rscript)
    for p in rlock['packages']:
        for kind in ['source','binary']:
            p[kind] = acquire_locked(p[kind],kind)
    for w in pylock['wheels']:
        w.update(acquire_locked(w,'wheels'))
    (root/'r-source-lock.json').write_text(json.dumps(rlock,indent=2)+'\n',encoding='utf-8')
    (root/'python-source-lock.json').write_text(json.dumps(pylock,indent=2)+'\n',encoding='utf-8')
    subprocess.run([str(args.python_base),'-I','-B','-m','venv',str(root/'python')],check=True)
    command = [str(root/'python/Scripts/python.exe'),'-B',str(here/'build.py'),str(root),'--r','--python']
    if args.offline:
        command.append('--offline')
    subprocess.run(command,check=True)
    print('Locked installation complete. Run fresh-session validation and audit before use.')


if __name__ == '__main__':
    main()
