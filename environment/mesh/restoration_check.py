"""Before/after immutability and semantic comparison for offline restoration."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
import stat
from pathlib import Path

from acquire import identity


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8', newline='\n')


def inventory(root, mode='content'):
    rows = [];paths=[]
    if root.exists():
        def raise_error(error):
            raise error
        for parent, dirs, files in os.walk(root,onerror=raise_error):
            dirs.sort()
            for name in sorted(files):
                paths.append(Path(parent)/name)
    def hash_file(path):
        info=path.stat()
        if not stat.S_ISREG(info.st_mode):
            return None
        row=dict(relative=path.relative_to(root).as_posix(),bytes=info.st_size)
        if mode=='metadata':
            return row|dict(mtime_ns=info.st_mtime_ns,ctime_ns=info.st_ctime_ns)
        try:
            with path.open('rb') as stream:
                digest=hashlib.file_digest(stream,'sha256').hexdigest()
        except OSError as exc:
            raise OSError(f'Cannot authenticate {path}: {exc}') from exc
        return row|dict(sha256=digest)
    with ThreadPoolExecutor(max_workers=8) as workers:
        for row in workers.map(hash_file,paths):
            if row is not None:
                rows.append(row)
    rows.sort(key=lambda x:x['relative'])
    payload=(json.dumps(rows,sort_keys=True,separators=(',',':'))+'\n')
    return dict(root=str(root), mode=mode, exists=root.exists(), files=rows,
                sha256=hashlib.sha256(payload.encode()).hexdigest(), bytes=sum(r['bytes'] for r in rows))


def compare(accepted, restored):
    original = read(accepted/'validation-summary.json')
    repeated = read(restored/'validation-summary.json')
    keys = ['status','scope','python','platform','packages','hdf5','r_runs',
            'deterministic_semantics','coordinate_order','metadata_authentication',
            'generalized_eigenvalue_error','orthogonality_error','eigen_residual',
            'bessel_half_order_relative_error','bessel_order5_values','hdf5_roundtrip',
            'python_to_r_matrix_market','stack_imbalance_detected']
    for key in keys:
        assert original[key] == repeated[key], ('validation comparison',key)
    assert original['status'] == 'pass'
    for result in [original,repeated]:
        assert result['process_tree']['child_detected'] and result['process_tree']['processes']>=2
        assert result['process_tree']['rss_bytes']>0
        for run in result['r_runs']:
            assert (run['vertices'],run['triangles'],run['projector_shape'])==(13,16,[3,13])
    records = []
    for root in [accepted,restored]:
        rlock=read(root/'r-source-lock.json');pylock=read(root/'python-source-lock.json')
        integrity=read(root/'installed-integrity.json')
        archives=[]
        for package in rlock['packages']:
            for kind in ['source','binary']:
                p=package[kind]
                archives.append(dict(package=package['package'],version=package['version'],kind=kind,
                    url=p['url'],bytes=p['bytes'],sha256=p['sha256']))
        for p in pylock['wheels']:
            archives.append({k:p[k] for k in ['package','version','url','bytes','sha256']}|dict(kind='wheel'))
        record=dict(R_runtime=rlock['runtime'],R_base_packages=rlock['base_packages'],
            R_packages={p['package']:p['version'] for p in integrity['r_packages']},
            archives=archives,python_freeze=(root/'python-freeze.txt').read_text(encoding='utf-8').splitlines(),
            numerical_config=read(root/'python-numerical-config.json'),pip_check=integrity['pip_check'],
            python_isolated_site_packages=integrity['python_isolated_site_packages'])
        command=read(root/'validation-summary.json')['r_commands'][0]
        session_dir=Path(command[-1])
        r=read(session_dir/'result.json')
        def normalize(value):
            return value.replace(str(root).replace('\\','/'),'ENVIRONMENT_ROOT').replace(str(root),'ENVIRONMENT_ROOT')
        record['R_result']=json.loads(normalize(json.dumps(r)))
        # JSON escapes backslashes, so canonical R paths above use forward slashes.
        record['R_session']=normalize((session_dir/'session.txt').read_text(encoding='utf-8'))
        records.append(record)
    assert records[0] == records[1], [k for k in records[0] if records[0][k]!=records[1][k]]
    return dict(status='pass',exact_validation_fields=keys,package_and_runtime_comparison='exact after environment-path normalization',
        R_packages=records[0]['R_packages'],python_freeze=records[0]['python_freeze'],
        authenticated_archives=records[0]['archives'],original_semantic_hashes=original['r_runs'][0]['semantic_hashes'],
        restored_semantic_hashes=repeated['r_runs'][0]['semantic_hashes'],original_numerical_results={k:original[k] for k in keys if k.startswith(('generalized','orthogonality','eigen','bessel'))},
        restored_numerical_results={k:repeated[k] for k in keys if k.startswith(('generalized','orthogonality','eigen','bessel'))},
        original_process_tree=original['process_tree'],restored_process_tree=repeated['process_tree'],
        expected_nonsemantic_differences=['environment paths','process IDs and RSS','installation timestamps and path-specific metadata'],
        installed_directory_byte_equality_required=False)


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest='action',required=True)
    snap=sub.add_parser('snapshot');snap.add_argument('roots',type=Path);snap.add_argument('destination',type=Path)
    verify=sub.add_parser('verify');verify.add_argument('before',type=Path);verify.add_argument('destination',type=Path)
    comp=sub.add_parser('compare');comp.add_argument('accepted',type=Path);comp.add_argument('restored',type=Path);comp.add_argument('destination',type=Path)
    args=ap.parse_args()
    if args.action=='snapshot':
        rows=[]
        for entry in read(args.roots)['roots']:
            root=entry['path'];mode=entry['mode']
            print('Inventory',mode,root,flush=True);rows.append(inventory(Path(root),mode))
        write(args.destination,dict(schema_version=1,roots=rows))
    elif args.action=='verify':
        result=[]
        for before in read(args.before)['roots']:
            print('Verifying',before['root'],flush=True)
            after=inventory(Path(before['root']),before['mode'])
            assert before==after,('immutable root changed',before['root'])
            result.append(dict(root=before['root'],mode=before['mode'],exists=before['exists'],files=len(before['files']),bytes=before['bytes'],sha256=before['sha256'],unchanged=True))
        write(args.destination,dict(schema_version=1,status='pass',roots=result))
    else:
        write(args.destination,compare(args.accepted.resolve(),args.restored.resolve()))
    print('PASS',args.action,flush=True)


if __name__=='__main__':
    main()
