"""Explicit isolated CPU build from resolved official wheel identities.

Acquisition requires --acquire. Installation itself is always offline/no-index.
No package resolution or substitution is performed here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import shutil
import urllib.request
from urllib.parse import urlparse, unquote


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--acquire', action='store_true')
    parser.add_argument('--wheel-cache', type=Path,
                        help='Authenticated cached wheels for offline restoration')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    lock = json.loads((here/'source-lock.json').read_text())
    for item in lock['runtime']:
        assert sha(item['path']) == item['sha256'], 'Runtime identity mismatch'
    root = args.root.resolve()
    repo = here.parents[1]
    if root == repo or repo in root.parents:
        raise ValueError('Environment must be outside Git')
    if (root/'installed.json').exists():
        raise ValueError('Refusing already installed environment')
    wheels = root/'wheels'; wheels.mkdir(parents=True, exist_ok=True)
    records = []
    for item in lock['packages']:
        url = item['url']
        if urlparse(url).hostname != 'files.pythonhosted.org':
            raise ValueError('Unexpected wheel source')
        target = wheels/Path(unquote(urlparse(url).path)).name
        if not target.exists() and args.wheel_cache:
            cached = args.wheel_cache/target.name
            if not cached.is_file() or sha(cached) != item['sha256']:
                raise ValueError('Offline cached wheel unavailable or corrupt: '+target.name)
            shutil.copyfile(cached, target)
        if not target.exists():
            if not args.acquire:
                raise ValueError('Offline wheel unavailable: '+target.name)
            with urllib.request.urlopen(url, timeout=120) as response:
                with target.open('xb') as stream:
                    while chunk := response.read(1024*1024):
                        stream.write(chunk)
        assert sha(target) == item['sha256'], 'Wheel identity mismatch'
        records.append(dict(name=item['name'], version=item['version'], filename=target.name,
                            bytes=target.stat().st_size, sha256=item['sha256'], url=url))
    python = root/'python/Scripts/python.exe'
    commands = []
    if not python.exists():
        command = [lock['runtime'][0]['path'], '-I', '-m', 'venv', str(root/'python')]
        subprocess.run(command, check=True); commands.append(command)
    # Existing destination may contain only the freshly bootstrapped pip.
    installed = json.loads(subprocess.check_output([str(python), '-I', '-m', 'pip', '--isolated', 'list', '--format=json']))
    assert {p['name'].lower() for p in installed} <= {'pip'}, 'Nonempty package library'
    command = [str(python), '-I', '-m', 'pip', '--isolated', 'install', '--no-index',
               '--no-deps', '--require-hashes', '--find-links', str(wheels),
               '-r', str(here/'requirements.lock.txt')]
    subprocess.run(command, check=True); commands.append(command)
    subprocess.run([str(python), '-I', '-m', 'pip', '--isolated', 'check'], check=True)
    installed = json.loads(subprocess.check_output([str(python), '-I', '-m', 'pip', '--isolated', 'list', '--format=json']))
    normalize = lambda s: s.lower().replace('_', '-')
    assert {normalize(x['name']): x['version'] for x in installed} == {
        'pip': lock['pip'], **{normalize(x['name']): x['version'] for x in lock['packages']}}
    result = dict(schema='bsfm.sampler-layer5-cpu-build.v1', status='PASS',
                  root_machine_local=str(root), commands=commands, packages=installed,
                  wheels=records, lock_sha256=sha(here/'source-lock.json'),
                  requirements_sha256=sha(here/'requirements.lock.txt'),
                  python_executable_sha256=sha(python), offline_install=True)
    (root/'installed.json').write_text(json.dumps(result, indent=2)+'\n', newline='\n')
    print('PASS: authenticated wheels, offline isolated install, complete package-set check')


if __name__ == '__main__':
    main()
