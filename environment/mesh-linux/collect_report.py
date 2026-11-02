"""Collect read-only package/version evidence after an allocated R build ends.

This does not rerun R or modify the approved build specification or installation.
Installed DESCRIPTION metadata is distinguished from the builder's fresh-process
version and namespace validation. Failed or incomplete builds cannot pass.
"""
import argparse
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def description(path):
    fields = {}
    if path.is_file():
        for line in path.read_text(errors='replace').splitlines():
            if line and not line[0].isspace() and ':' in line:
                key, value = line.split(':', 1)
                fields[key] = value.strip()
    return fields


def collect(root, lock_path, specification_sha256):
    receipt_path = root / 'build-receipt.json'
    receipt = json.loads(receipt_path.read_text())
    lock = json.loads(lock_path.read_text())
    library = root / 'r-library'
    packages = []
    for expected in lock['packages']:
        path = library / expected['package'] / 'DESCRIPTION'
        fields = description(path)
        packages.append({'package': expected['package'], 'expected_version': expected['version'],
                         'installed_version': fields.get('Version'),
                         'version_matches': fields.get('Version') == expected['version'],
                         'description': str(path),
                         'description_sha256': sha(path) if path.is_file() else None,
                         'installed_directory_inside_library': path.is_file() and path.resolve().is_relative_to(library.resolve()),
                         'built': fields.get('Built')})
    validations = [c for c in receipt['commands'] if c['label'] == 'validate']
    log = root / 'logs/validate.log'
    fresh_pass = (len(validations) == 1 and validations[0].get('returncode') == 0
                  and log.is_file() and 'LOCKED_R_PACKAGES_AND_NAMESPACE_ISOLATION_PASS'
                  in log.read_text(errors='replace'))
    runtime_paths = list((root / 'R').glob('lib*/R/library/base/DESCRIPTION'))
    runtime = description(runtime_paths[0]).get('Version') if len(runtime_paths) == 1 else None
    passed = (receipt['status'] == 'passed' and fresh_pass and runtime == '4.5.3'
              and len(packages) == 33 and all(p['version_matches'] and
                  p['installed_directory_inside_library'] for p in packages))
    return {'schema': 'bsfm.linux-r-package-validation.v1',
            'status': 'passed' if passed else 'not_passed',
            'code_commit': receipt['code_commit'], 'job_id': receipt['slurm_job_id'],
            'approved_specification_sha256': specification_sha256,
            'build_status': receipt['status'], 'build_receipt_sha256': sha(receipt_path),
            'package_source_lock_sha256': sha(lock_path), 'output_root': str(root),
            'R_expected_version': '4.5.3', 'R_installed_metadata_version': runtime,
            'fresh_R_version_and_namespace_validation_passed': fresh_pass,
            'packages': packages,
            'logs': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': sha(p)}
                     for p in sorted((root / 'logs').glob('*.log'))],
            'interpretation': 'Runtime build and package validation only; no mesh-output or SCT reproducibility claim. External conda system dependencies remain.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--build-root', type=Path, required=True)
    ap.add_argument('--source-lock', type=Path, required=True)
    ap.add_argument('--specification-sha256', required=True)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    report = collect(args.build_root, args.source_lock, args.specification_sha256)
    with args.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2) + '\n')
    print(report['status'])


if __name__ == '__main__':
    main()
