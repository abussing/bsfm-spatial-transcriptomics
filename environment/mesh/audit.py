"""Authenticate the external environment and emit small inventory metadata."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys

from acquire import identity, dcf
from build import runtime_tree


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('root', type=Path)
    args = ap.parse_args()
    root = args.root.resolve()
    assert Path(sys.prefix).resolve() == root / 'python'
    lock = json.loads((root/'r-source-lock.json').read_text(encoding='utf-8'))
    archive_count = 0
    packages = []
    for row in lock['packages']:
        for kind in ['binary', 'source']:
            rec = row[kind]
            measured = identity(Path(rec['path']))
            assert all(measured[k] == rec[k] for k in ['bytes', 'sha256'])
            archive_count += 1
        package = root/'r-library'/row['package']
        description = package/'DESCRIPTION'
        actual = dcf(description.read_text(encoding='utf-8'))[0]
        assert actual['Package'] == row['package'] and actual['Version'] == row['version']
        tree = runtime_tree(package)
        metadata = [identity(p) for p in [description, package/'Meta/package.rds'] if p.exists()]
        packages.append(dict(package=row['package'], version=row['version'],
                             files=len(tree['files']), tree_sha256=tree['sha256'], metadata=metadata))
    rs = Path(lock['runtime']['path'])
    assert identity(rs) == lock['runtime']
    tree = runtime_tree(rs.parents[2])
    before = json.loads((root/'immutable-runtime-before.json').read_text(encoding='utf-8'))
    assert tree['sha256'] == before['sha256']
    pylock = json.loads((root/'python-source-lock.json').read_text(encoding='utf-8'))
    for wheel in pylock['wheels']:
        actual = identity(Path(wheel['path']))
        assert actual['sha256'] == wheel['sha256'] and actual['bytes'] == wheel['bytes']
        assert importlib.metadata.version(wheel['package']) == wheel['version']
        installed = Path(importlib.metadata.distribution(wheel['package']).locate_file('')).resolve()
        assert installed.is_relative_to(root/'python/Lib/site-packages')
    base = Path(sys.base_prefix)
    runtimes = [identity(p) for p in [Path(sys.executable), Path(sys._base_executable),
                base/'python312.dll', base/'python3.dll', root/'python/pyvenv.cfg']]
    bootstrap = [identity(p) for p in sorted((base/'Lib/ensurepip/_bundled').glob('*.whl'))]
    assert len(bootstrap) == 1 and 'pip-23.2.1-' in bootstrap[0]['path']
    cfg = (root/'python/pyvenv.cfg').read_text(encoding='utf-8')
    assert 'include-system-site-packages = false' in cfg
    assert importlib.metadata.version('pip') == '23.2.1'
    check = subprocess.check_output([sys.executable, '-B', '-m', 'pip', 'check'], text=True)
    assert 'No broken requirements found' in check
    code = [identity(p) for p in sorted(Path(__file__).parent.glob('*')) if p.suffix in ['.py', '.R']]
    record = dict(schema_version=1, status='pass', r_packages=packages,
        authenticated_r_archives=archive_count, authenticated_python_wheels=len(pylock['wheels']),
        r_runtime_tree=dict(root=str(rs.parents[2]), files=len(tree['files']), sha256=tree['sha256'],
                            unchanged_since_before_installation=True),
        python_runtime=runtimes, python_bootstrap=bootstrap, python_sys_path=sys.path,
        python_isolated_site_packages=True, pip_check=check.strip(), environment_tools=code)
    (root/'installed-integrity.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['r_packages','environment_tools','python_sys_path']},indent=2))


if __name__ == '__main__':
    main()
