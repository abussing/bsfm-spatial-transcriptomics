"""Isolated exact-version environment; build ml_dtypes for glibc 2.17."""
import argparse
import hashlib
import json
import os
import platform
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import venv


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--expected-commit', required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip() == args.expected_commit
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
    assert (platform.system(), platform.machine(), platform.python_version()) == ('Linux', 'x86_64', '3.11.14')
    root = Path('/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4')
    root.mkdir(exist_ok=False)
    cache = root / 'archives'
    cache.mkdir()
    wheels = root / 'wheels'
    wheels.mkdir()
    old_cache = root.parent / 'sampler-layer9-cpu-20261103-source3/archives'
    lockpath = repo / 'docs/sampler/review-layer9-20261103/LINUX_ENVIRONMENT_PROPOSAL.json'
    lock = json.loads(lockpath.read_text())['packages']
    buildpath = Path(__file__).with_name('BUILD_DEPENDENCIES.json')
    build = json.loads(buildpath.read_text())
    report = dict(status='incomplete', git_commit=args.expected_commit,
                  scope='Environment only; numerical validation pending',
                  script_sha256=sha(__file__), runtime_lock_sha256=sha(lockpath),
                  build_lock_sha256=sha(buildpath), archives=[],
                  base_python=sys.executable, base_python_sha256=sha(sys.executable),
                  glibc=platform.libc_ver(), tools={},
                  loaded_modules=os.environ.get('LOADEDMODULES'),
                  library_path=os.environ.get('LD_LIBRARY_PATH'))
    env = dict(os.environ, PYTHONNOUSERSITE='1', JAX_PLATFORMS='cpu',
               JAX_ENABLE_X64='true', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               CMAKE_BUILD_PARALLEL_LEVEL='2', PIP_NO_INDEX='1', PIP_NO_CACHE_DIR='1')

    def run(command):
        with (root / 'build.log').open('a') as stream:
            stream.write(json.dumps(command) + '\n')
            stream.flush()
            subprocess.run(command, stdout=stream, stderr=subprocess.STDOUT, check=True, env=env)

    def fetch(row):
        dest = cache / row['url'].rsplit('/', 1)[-1]
        old = old_cache / dest.name
        if old.exists() and sha(old) == row['sha256']:
            shutil.copyfile(old, dest)
        else:
            with urllib.request.urlopen(row['url'], timeout=120) as source, dest.open('xb') as target:
                shutil.copyfileobj(source, target)
        assert sha(dest) == row['sha256'], dest.name
        report['archives'].append(dict(name=dest.name, sha256=sha(dest), bytes=dest.stat().st_size))
        return dest

    try:
        for tool in ('gcc', 'g++'):
            executable = shutil.which(tool)
            assert executable, tool
            report['tools'][tool] = dict(path=executable, sha256=sha(executable),
                version=subprocess.check_output([executable, '--version'], text=True).splitlines()[0])
        runtime = {r['name']: fetch(r) for r in lock if r['name'] != 'ml_dtypes'}
        build_archives = {r['name']: fetch(r) for r in build}
        venv.create(root / 'build-python', with_pip=True, system_site_packages=False)
        bp = str(root / 'build-python/bin/python')
        req = root / 'build-requirements.txt'
        build_wheels = [runtime['numpy']] + [p for n, p in build_archives.items() if n != 'ml_dtypes']
        req.write_text(''.join(f'{p} --hash=sha256:{sha(p)}\n' for p in build_wheels))
        run([bp, '-I', '-m', 'pip', 'install', '--no-deps', '--require-hashes', '-r', str(req)])
        env['PATH'] = str(root / 'build-python/bin') + os.pathsep + env['PATH']
        for tool in ('cmake', 'ninja'):
            executable = str(root / 'build-python/bin' / tool)
            report['tools'][tool] = dict(path=executable, sha256=sha(executable),
                version=subprocess.check_output([executable, '--version'], text=True, env=env).splitlines()[0])
        run([bp, '-I', '-m', 'pip', 'wheel', '--no-deps', '--no-build-isolation',
             '--wheel-dir', str(wheels), str(build_archives['ml_dtypes'])])
        built = list(wheels.glob('ml_dtypes-0.6.0-*.whl'))
        assert len(built) == 1
        report['built_wheel'] = dict(name=built[0].name, sha256=sha(built[0]), bytes=built[0].stat().st_size)
        runtime['ml_dtypes'] = built[0]
        req = root / 'requirements.lock.txt'
        req.write_text(''.join(f'{p} --hash=sha256:{sha(p)}\n' for p in runtime.values()))
        venv.create(root / 'python', with_pip=True, system_site_packages=False)
        python = str(root / 'python/bin/python')
        run([python, '-I', '-m', 'pip', 'install', '--no-deps', '--require-hashes', '-r', str(req)])
        run([python, '-I', '-m', 'pip', 'check'])
        probe = '''import importlib.metadata as m, json, site, sys
from pathlib import Path
import numpy, scipy, jax, jaxlib, blackjax, ml_dtypes
assert not site.ENABLE_USER_SITE
assert jax.default_backend() == 'cpu' and jax.config.x64_enabled
mods={x.__name__:str(Path(x.__file__).resolve()) for x in (numpy,scipy,jax,jaxlib,blackjax,ml_dtypes)}
assert all(Path(p).is_relative_to(sys.prefix) for p in mods.values())
packages={d.metadata['Name'].lower().replace('_','-'):d.version for d in m.distributions()}
lock=json.loads(Path(sys.argv[1]).read_text())['packages']
assert all(packages[r['name'].lower().replace('_','-')]==r['version'] for r in lock)
assert not {'scikit-build-core','pathspec','packaging','cmake','ninja'}.intersection(packages)
Path(sys.argv[2]).write_text(json.dumps(dict(packages=packages,module_paths=mods,executable=sys.executable,base_prefix=sys.base_prefix,cpu=True,x64=True),indent=2)+'\\n')
'''
        run([python, '-I', '-c', probe, str(lockpath), str(root / 'package-validation.json')])
        report['status'] = 'environment_restored_numerical_validation_pending'
        report['package_report_sha256'] = sha(root / 'package-validation.json')
    finally:
        (root / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
