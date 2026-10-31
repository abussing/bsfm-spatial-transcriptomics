"""Thin sequential orchestration; fitting and deep validation belong to response_run."""
import argparse
import copy
from pathlib import Path
import shutil
import time

import psutil

from .raw_preflight import require, sha256_file
from .response_contract import (REPO, CONFIG, contract, load_json, identities,
                                require_clean_code, file_record, validate_json)
from .response_run import run as run_section
from .response_validate import fast_validate_bundle
from .source_attestation import source_session, check_attestation, final_authentication
from .production_state import (atomic_json, layout, run_lock, new_attempt,
                               cleanup_attempt, now, plain_directory)

POLICY = REPO/'config/preprocessing/production-run.json'


def policy(path):
    require(sha256_file(path) == sha256_file(POLICY), 'Unrecognized production policy')
    value = load_json(path)
    require(value['concurrency'] == 1 and value['minimum_available_ram_bytes'] == 7*1024**3
            and value['minimum_free_disk_bytes'] == 10*1024**3, 'Unapproved resource policy')
    return value


def resource_observation(root):
    return {'observed_at': now(), 'available_ram_bytes': psutil.virtual_memory().available,
            'free_disk_bytes': shutil.disk_usage(root).free}


def enforce_resources(measured, config):
    require(measured['available_ram_bytes'] >= config['minimum_available_ram_bytes'], 'Available RAM below 7 GiB')
    require(measured['free_disk_bytes'] >= config['minimum_free_disk_bytes'], 'Free destination space below 10 GiB')


def specification(root, source, envroot, config, production_config, code, start):
    _, _, _, registry = contract(config)
    schema_paths = ['production-specification.schema.json', 'production-ledger.schema.json', 'production-manifest.schema.json']
    return {'schema': 'bsfm.production-run-specification.v1', 'run_root': str(root),
            'code': code, 'source': {k: start[k] for k in ('path', 'bytes', 'sha256')},
            'source_initial_stat': start['initial_stat'], 'environment_root': str(envroot),
            'identities': identities(config, envroot), 'single_section_configuration': load_json(config),
            'policy': policy(production_config), 'policy_sha256': sha256_file(production_config),
            'schemas': {p: sha256_file(REPO/'schemas/preprocessing'/p) for p in schema_paths},
            'section_order': [s['section'] for s in registry['sections']]}


def checkpoint(root, ledger, event, section=None):
    ledger['events'].append({'time': now(), 'event': event, 'section': section})
    validate_json(ledger, 'production-ledger.schema.json')
    atomic_json(root/'run-ledger.json', ledger)


def initial_ledger(digest, order):
    return {'schema': 'bsfm.production-run-ledger.v1', 'run_spec_sha256': digest,
            'status': 'running', 'section_order': order, 'sessions': [], 'events': [],
            'sections': {s: {'state': 'pending', 'attempts': [], 'resources': [], 'checks': [],
                              'manifest': None, 'receipt': None} for s in order}}


def cleanup_success(root, ledger, section, checked):
    entry = ledger['sections'][section]
    # Only the attempt identified by the authenticated promoted execution is eligible.
    for attempt in entry['attempts']:
        if attempt['id'] != checked['attempt_id'] or attempt['state'] == 'failed':
            continue
        path = root/'attempts'/attempt['id']
        if (path/'failure.json').exists():
            attempt['cleanup'] = 'retained_failed'
            checkpoint(root, ledger, 'cleanup_retained_failed', section)
            continue
        if attempt['cleanup'] in ('removed', 'already_absent'):
            continue
        attempt['state'] = 'promoted'
        attempt['cleanup'] = 'pending'
        checkpoint(root, ledger, 'cleanup_intent', section)
        attempt['cleanup'] = cleanup_attempt(root, path)
        checkpoint(root, ledger, 'cleanup_complete', section)


def inventory(root, spec, config, digest):
    require(set(p.name for p in (root/'sections').iterdir()) == set(spec['section_order']),
            'Completion requires exactly all 19 finalized sections')
    result = []
    for section in spec['section_order']:
        checked = fast_validate_bundle(root/'sections'/section, section, spec['source'],
                                       Path(spec['environment_root']), config, digest)
        result.append({'section': section, 'manifest': {**checked['manifest'],
                       'path': 'sections/'+section+'/manifest.json'},
                       'validation': checked['validation'], 'original_deep_validation': 'pass'})
    require(len(result) == 19, 'All-19 completion required')
    return result


def execute(root, source, envroot, config=CONFIG, production_config=POLICY):
    code = require_clean_code()
    config = Path(config).resolve(); envroot = Path(envroot).resolve(); source = Path(source).resolve()
    rules = policy(production_config)
    root = plain_directory(root)
    require(not root.is_relative_to(REPO), 'Production artifacts must stay outside Git')
    root = layout(root)
    expected = load_json(REPO/'docs/preprocessing/audits/20261030_raw/manifest.json')['source']
    with run_lock(root), source_session(source, expected) as (token, start):
        spec = specification(root, source, envroot, config, production_config, code, start)
        validate_json(spec, 'production-specification.schema.json')
        spec_path = root/'run-specification.json'
        if spec_path.exists():
            require(load_json(spec_path) == spec, 'Incompatible resume specification')
        else:
            require(not any((root/'sections').iterdir()) and not any((root/'attempts').iterdir())
                    and not (root/'run-ledger.json').exists() and not (root/'run-manifest.json').exists(),
                    'Existing artifacts without run specification')
            atomic_json(spec_path, spec, replace=False)
        digest = sha256_file(spec_path)
        ledger_path = root/'run-ledger.json'
        if ledger_path.exists():
            ledger = load_json(ledger_path)
            validate_json(ledger, 'production-ledger.schema.json')
            require(ledger['run_spec_sha256'] == digest and ledger['section_order'] == spec['section_order']
                    and set(ledger['sections']) == set(spec['section_order']), 'Incompatible resume ledger')
        else:
            require(not any((root/'sections').iterdir()) and not any((root/'attempts').iterdir()),
                    'Missing ledger with existing scientific artifacts')
            ledger = initial_ledger(digest, spec['section_order'])
        session = {'start': now(), 'source_start': start, 'end': None, 'source_final': None}
        ledger['sessions'].append(session)
        ledger['status'] = 'running'
        checkpoint(root, ledger, 'session_start')
        section = None
        try:
            for section in spec['section_order']:
                require(require_clean_code() == code and identities(config, envroot) == spec['identities'],
                        'Production identities changed')
                require(sha256_file(spec_path) == digest and policy(production_config) == rules, 'Run configuration changed')
                check_attestation(token, source, expected)
                entry = ledger['sections'][section]
                measured = resource_observation(root)
                entry['resources'].append(measured)
                checkpoint(root, ledger, 'resource_observation', section)
                enforce_resources(measured, rules)
                final = root/'sections'/section
                if final.exists():
                    checked = fast_validate_bundle(final, section, spec['source'], envroot, config, digest)
                    require(entry['manifest'] is None or entry['manifest'] == checked['manifest'], 'Finalized manifest changed since checkpoint')
                    entry['checks'].append({'time': now(), 'kind': checked['validation']})
                    entry['state'] = 'promoted'; entry['manifest'] = checked['manifest']
                    checkpoint(root, ledger, 'resume_promoted', section)
                    cleanup_success(root, ledger, section, checked)
                    continue
                require(entry['state'] != 'promoted' and entry['manifest'] is None, 'Previously promoted bundle is missing')
                for previous in entry['attempts']:
                    if previous['state'] == 'started':
                        previous['state'] = 'interrupted'
                attempt = new_attempt(root, section)
                record = {'id': attempt.name, 'state': 'started', 'cleanup': 'retained', 'started': now(), 'ended': None}
                entry['attempts'].append(record); entry['state'] = 'running'
                checkpoint(root, ledger, 'attempt_start', section)
                started = time.monotonic()
                try:
                    receipt = run_section(section, source, envroot, config, root, attestation=token,
                                          run_spec_sha256=digest, attempt=attempt)
                    checked = fast_validate_bundle(final, section, spec['source'], envroot, config, digest)
                except BaseException:
                    record['state'] = 'failed'; record['ended'] = now()
                    entry['state'] = 'failed'
                    checkpoint(root, ledger, 'attempt_failed_retained', section)
                    raise
                record['state'] = 'promoted'; record['ended'] = now()
                entry['receipt'] = receipt; entry['manifest'] = checked['manifest']; entry['state'] = 'promoted'
                entry['checks'].append({'time': now(), 'kind': 'deep_before_promotion_plus_fast_after',
                                        'elapsed_seconds': time.monotonic()-started})
                checkpoint(root, ledger, 'promoted', section)
                cleanup_success(root, ledger, section, checked)
            ordered = inventory(root, spec, config, digest)
            final_source = final_authentication(token, source, expected)
            require(require_clean_code() == code and specification(root, source, envroot, config, production_config, code, start) == spec,
                    'Closure identities changed')
            session['source_final'] = final_source; session['end'] = now()
            ledger['status'] = 'closing'
            checkpoint(root, ledger, 'closure_validated')
            result = {'schema': 'bsfm.production-run-manifest.v1', 'status': 'complete', 'pass': True,
                      'run_spec_sha256': digest, 'run_specification': file_record(spec_path),
                      'code': code, 'identities': spec['identities'], 'policy_sha256': spec['policy_sha256'],
                      'source_start': start, 'source_final': final_source, 'section_order': spec['section_order'],
                      'sections': ordered, 'sessions': copy.deepcopy(ledger['sessions']),
                      'section_records': copy.deepcopy(ledger['sections']), 'completed_at': now()}
            validate_json(result, 'production-manifest.schema.json')
            final_path = root/'run-manifest.json'
            if final_path.exists():
                saved = load_json(final_path)
                validate_json(saved, 'production-manifest.schema.json')
                for key in ('run_spec_sha256', 'run_specification', 'code', 'identities', 'policy_sha256', 'section_order', 'sections'):
                    require(saved[key] == result[key], 'Existing completion artifact mismatch: '+key)
                for phase in ('source_start', 'source_final'):
                    require({k:saved[phase][k] for k in ('path','bytes','sha256','initial_stat')} ==
                            {k:result[phase][k] for k in ('path','bytes','sha256','initial_stat')}, 'Completion source mismatch')
                result = saved
            else:
                atomic_json(final_path, result, replace=False)
            ledger['status'] = 'complete'
            checkpoint(root, ledger, 'run_complete')
            return result
        except BaseException as exc:
            ledger['status'] = 'failed'; session['end'] = now()
            session['error'] = str(exc)
            checkpoint(root, ledger, 'run_stopped', section)
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-root', type=Path, required=True)
    parser.add_argument('--raw-source', type=Path, required=True)
    parser.add_argument('--environment', type=Path, required=True)
    parser.add_argument('--config', type=Path, default=CONFIG)
    parser.add_argument('--production-config', type=Path, default=POLICY)
    args = parser.parse_args()
    result = execute(args.run_root, args.raw_source, args.environment, args.config, args.production_config)
    print(result['status'])


if __name__ == '__main__':
    main()
