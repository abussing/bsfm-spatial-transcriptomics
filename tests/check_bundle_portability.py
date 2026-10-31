"""Integration gate for an already isolated six-file review bundle.

Requires all recorded original log paths to be absent. Revalidates raw source,
environment and the entire copied bundle, including independent recorrection.
Never fits SCT or changes/deletes the original attempt directory.
"""
import argparse
from pathlib import Path

from bsfm.preprocessing.raw_preflight import require
from bsfm.preprocessing.execution_evidence import authenticate_process
from bsfm.preprocessing.response_contract import REPO, contract, load_json, save_json, file_record
from bsfm.preprocessing.response_validate import validate_bundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'raw-source', 'environment', 'config', 'work-dir'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    work = args.work_dir.resolve()
    require(not work.is_relative_to(REPO) and not work.is_relative_to(bundle), 'Use separate external validation work directory')
    _, _, spec, _ = contract(args.config)
    require(set(p.name for p in bundle.iterdir()) == set(spec['required_files']) | {'manifest.json'}, 'Copy must contain exactly six files')
    execution = load_json(bundle/'execution.json')
    validation = load_json(bundle/'validation.json')
    processes = [execution['normalization']['process'], execution['transport_readback']['process'],
                 validation['independent_readback']['process']]
    original_logs = []
    for process in processes:
        authenticate_process(process)
        original = process['log']['path']
        require(not Path(original).exists(), 'Original log must be unavailable for this integration test')
        original_logs.append(original)
    before = {p.name: file_record(p) for p in bundle.iterdir()}
    result = validate_bundle(bundle, args.raw_source.resolve(), args.environment.resolve(), args.config, work)
    after = {p.name: file_record(p) for p in bundle.iterdir()}
    require(before == after, 'Independent validation modified the copied bundle')
    report = {'schema': 'bsfm.bundle-portability-review.v1', 'status': 'pass',
              'bundle': str(bundle), 'files': after, 'required_file_count': 6,
              'original_logs_absent': original_logs, 'bundle_unchanged': True,
              'full_raw_and_environment_revalidation': True, 'validation': result,
              'scope': 'Uncommitted S00 review artifact; not a future all-section production artifact'}
    save_json(work/'portability.json', report)
    print('PASS: isolated six-file bundle; all original logs absent; full independent validation; copy unchanged')


if __name__ == '__main__':
    main()
