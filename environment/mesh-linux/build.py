"""Build the locked R mesh packages in a fresh Linux prefix on an allocated node.

No dependency resolution, downloads, historical-code imports or scientific fits.
The existing conda toolchain is an explicit read-only external dependency.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import subprocess
import tarfile


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def checked_source(cache, record):
    path = cache / PureWindowsPath(record['path']).name
    if path.stat().st_size != record['bytes'] or digest(path) != record['sha256']:
        raise ValueError('Source identity mismatch: ' + str(path))
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('repository', 'sources', 'toolchain', 'udunits_headers', 'output'):
        ap.add_argument('--' + name.replace('_', '-'), type=Path, required=True)
    ap.add_argument('--code-commit', required=True)
    ap.add_argument('--jobs', type=int, default=4)
    args = ap.parse_args()
    if not os.environ.get('SLURM_JOB_ID'):
        raise RuntimeError('Use an allocated Slurm job, never the login node')
    if not re.fullmatch('[0-9a-f]{40}', args.code_commit) or not 1 <= args.jobs <= 4:
        raise ValueError('Exact commit and one to four build workers required')
    root = args.output.resolve()
    if root.exists():
        raise FileExistsError('Fresh output root required: ' + str(root))
    toolchain = args.toolchain.resolve()
    mesh = json.loads((args.repository / 'environment/mesh/r-source-lock.json').read_text())
    sct = json.loads((args.repository / 'environment/sctransform/source-lock.json').read_text())
    sources = {p['package']: checked_source(args.sources, p['source']) for p in mesh['packages']}
    runtime_source = checked_source(args.sources, sct['R_source'])
    packages = {p['package']: p for p in mesh['packages']}
    base = set(mesh['base_packages']) | {'R'}
    deps = {}
    for name, p in packages.items():
        needed = set()
        for field in ('Depends', 'Imports', 'LinkingTo'):
            for item in p['source_description'].get(field, '').split(','):
                if not item.strip():
                    continue
                dep = item.strip().split()[0]
                if dep not in packages and dep not in base:
                    raise ValueError('Unlocked dependency: ' + dep)
                if dep in packages:
                    needed.add(dep)
        deps[name] = needed
    order = []
    while len(order) < len(packages):
        ready = sorted(n for n in packages if n not in order and deps[n] <= set(order))
        if not ready:
            raise ValueError('Dependency cycle')
        order.extend(ready)
    tools = {name: toolchain / 'bin' / ('x86_64-conda-linux-gnu-' + exe)
             for name, exe in [('CC', 'gcc'), ('CXX', 'g++'), ('FC', 'gfortran')]}
    tools['MAKE'] = toolchain / 'bin/make'
    tool_ids = {name: {'path': str(path), 'sha256': digest(path)} for name, path in tools.items()}
    headers = args.udunits_headers.resolve()
    header_lock = json.loads(Path(__file__).with_name('udunits-headers.json').read_text())
    for name, expected in header_lock['header_sha256'].items():
        if digest(headers / name) != expected:
            raise ValueError('UDUNITS header identity mismatch: ' + name)
    root.mkdir(parents=True)
    for d in ('logs', 'tmp', 'build', 'r-library', 'compat-lib'):
        (root / d).mkdir()
    (root / 'compat-lib/libudunits2.so').symlink_to(toolchain / 'lib/libudunits2.so.0')
    prefix = root / 'R'
    env = os.environ.copy()
    for key in ('R_HOME', 'R_LIBS', 'R_PROFILE', 'R_PROFILE_USER', 'R_ENVIRON', 'R_ENVIRON_USER'):
        env.pop(key, None)
    env.update({k: str(v) for k, v in tools.items()})
    env.update(PATH=str(toolchain / 'bin') + ':/usr/bin:/bin',
               LD_LIBRARY_PATH=str(toolchain / 'lib'),
               PKG_CONFIG_PATH=str(toolchain / 'lib/pkgconfig'),
               CPPFLAGS=f'-I{headers} -I{toolchain}/include',
               LDFLAGS=f'-L{root}/compat-lib -L{toolchain}/lib -Wl,-rpath,{toolchain}/lib',
               R_LIBS_USER=str(root / 'r-library'), R_LIBS_SITE=str(root / 'r-library'),
               R_MAKEVARS_USER='/dev/null', R_MAKEVARS_SITE='/dev/null',
               TMPDIR=str(root / 'tmp'), LC_ALL='C',
               MAKEFLAGS=f'-j{args.jobs}', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
               UDUNITS2_XML_PATH=str(toolchain / 'share/udunits/udunits2.xml'))
    receipt = {'status': 'started', 'code_commit': args.code_commit,
               'slurm_job_id': os.environ['SLURM_JOB_ID'], 'toolchain': tool_ids,
               'toolchain_prefix': str(toolchain), 'install_order': order,
               'udunits_header_sha256': header_lock['header_sha256'],
               'conda_metadata_sha256': {p.name: digest(p) for p in sorted((toolchain / 'conda-meta').glob('*.json'))},
               'source_sha256': {'R': digest(runtime_source), **{n: digest(p) for n, p in sources.items()}},
               'external_dependency_limit': 'Conda compiler/sysroot/system libraries remain external; not a standalone or byte-reproducible environment',
               'commands': []}
    def save():
        (root / 'build-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    def run(label, argv, cwd=None):
        row = {'label': label, 'argv': list(map(str, argv)), 'cwd': str(cwd or root)}
        receipt['commands'].append(row); save()
        with (root / 'logs' / (label + '.log')).open('w') as log:
            result = subprocess.run(row['argv'], cwd=cwd or root, env=env,
                                    stdout=log, stderr=subprocess.STDOUT)
        row['returncode'] = result.returncode; save()
        if result.returncode:
            raise RuntimeError('Failed stage: ' + label)
        print('PASS', label, flush=True)
    save()
    try:
        with tarfile.open(runtime_source) as archive:
            archive.extractall(root / 'build', filter='data')
        build = root / 'build/R-4.5.3'
        run('configure', [build / 'configure', '--prefix=' + str(prefix), '--enable-R-shlib',
                         '--with-x=no', '--with-readline=no', '--without-recommended-packages'], build)
        run('make', [tools['MAKE'], '-j' + str(args.jobs)], build)
        run('install-runtime', [tools['MAKE'], 'install'], build)
        for name in order:
            argv = [prefix / 'bin/R', 'CMD', 'INSTALL', '--no-multiarch',
                    '--library=' + str(root / 'r-library')]
            if name == 'units':
                argv += [f'--configure-args=--with-udunits2-include={headers} --with-udunits2-lib={root}/compat-lib']
            run('package-' + name, argv + [sources[name]])
        validation = root / 'validate.R'
        expected = ','.join(json.dumps(n) + '=' + json.dumps(packages[n]['version']) for n in order)
        validation.write_text('args <- commandArgs(TRUE)\n'
            '.libPaths(c(args[1], .Library), include.site=FALSE)\n'
            'stopifnot(getRversion() == "4.5.3")\n'
            'wanted <- c(' + expected + ')\n'
            'for (p in names(wanted)) {\n'
            ' stopifnot(as.character(packageVersion(p)) == wanted[[p]])\n'
            ' loadNamespace(p)\n}\n'
            'for (p in loadedNamespaces()) {\n'
            ' loc <- normalizePath(getNamespaceInfo(asNamespace(p), "path"))\n'
            ' if (p %in% names(wanted)) stopifnot(startsWith(loc, paste0(normalizePath(args[1]), "/")))\n'
            ' else stopifnot(startsWith(loc, paste0(normalizePath(.Library), "/")))\n}\n'
            'writeLines(capture.output(sessionInfo()), args[2])\n'
            'cat("LOCKED_R_PACKAGES_AND_NAMESPACE_ISOLATION_PASS\\n")\n')
        run('validate', [prefix / 'bin/Rscript', '--vanilla', validation,
                         root / 'r-library', root / 'session-info.txt'])
        receipt['status'] = 'passed'
    except Exception as exc:
        receipt.update(status='failed', error=str(exc))
        raise
    finally:
        save()


if __name__ == '__main__':
    main()
