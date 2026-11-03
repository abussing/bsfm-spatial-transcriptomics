"""Explicit software/run and target identities for complete checkpoint v1."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import numpy as np

from .contracts import logical_hash, noise_inputs, SHARING
from .layer6 import N_INNER, SIGMA2_PRIOR_SHAPE, ELL_ETA
from .checkpoint_rng import json_text, parse_json, exact_keys

SCHEMA = 'bsfm.complete-checkpoint.v1'
CONTRACT_SCHEMA = 'bsfm.checkpoint-contract.v1'


def digest(value):
    return hashlib.sha256(json_text(value).encode('utf-8')).hexdigest()


def require_hash(value, length=64):
    if not isinstance(value, str) or not re.fullmatch('[a-f0-9]{%d}' % length, value):
        raise ValueError('Explicit lowercase content identity required')


def software_record(record, expected_sha256):
    exact_keys(record, ('git_commit', 'clean_tree', 'run_config_sha256',
                        'environment_lock_sha256', 'environment_identity'))
    require_hash(record['git_commit'], 40)
    for name in ('run_config_sha256', 'environment_lock_sha256'):
        require_hash(record[name])
    if (type(record['clean_tree']) is not bool or not isinstance(record['environment_identity'], str)
            or not record['environment_identity']):
        raise ValueError('Explicit clean-tree declaration and environment identity required')
    require_hash(expected_sha256)
    if digest(record) != expected_sha256:
        raise ValueError('Software/run contract does not match supplied authenticated identity')
    return parse_json(json_text(record))


def fixed_requirements():
    return dict(chronology_schema='bsfm.layer6-complete-sweep.v1', n_inner=N_INNER,
                sharing=SHARING, ell_eta=ELL_ETA, sigma2_prior_shape=SIGMA2_PRIOR_SHAPE,
                layer6_source_sha256=hashlib.sha256(Path(__file__).with_name('layer6.py').read_bytes()).hexdigest())


@dataclass(frozen=True)
class CheckpointContract:
    json: str
    sha256: str


def build_checkpoint_contract(target, *, b_sigma2, software, expected_software_sha256):
    """Caller authenticates external commit/config/environment; no Git invocation."""
    target._validate_identities()
    y = target.inputs.arrays['Y']
    noise_inputs(y, np.zeros_like(y), np.ones_like(y), SIGMA2_PRIOR_SHAPE, b_sigma2)
    record = dict(schema=CONTRACT_SCHEMA, target_identity=target.identity,
        input_identity=target.inputs.identity_json, geometry_identity=target.geometry.identity_json,
        rule_identity=target.rule.identity_json, spectral_identity=target.geometry.spectral_identity,
        factor_ids=list(target.factor_ids), b_sigma2_sha256=logical_hash(b_sigma2),
        fixed=fixed_requirements(), software=software_record(software, expected_software_sha256),
        software_sha256=expected_software_sha256)
    return CheckpointContract(json_text(record), digest(record))


def validate_contract(contract, target, b_sigma2):
    if not isinstance(contract, CheckpointContract):
        raise ValueError('Explicit authenticated checkpoint contract required')
    record = parse_json(contract.json)
    exact_keys(record, ('schema','target_identity','input_identity','geometry_identity','rule_identity',
                        'spectral_identity','factor_ids','b_sigma2_sha256','fixed','software','software_sha256'))
    if contract.sha256 != digest(record) or contract.json != json_text(record):
        raise ValueError('Checkpoint contract mutated or noncanonical')
    expected = build_checkpoint_contract(target, b_sigma2=b_sigma2, software=record['software'],
                                         expected_software_sha256=record['software_sha256'])
    if expected != contract:
        raise ValueError('Target/input/geometry/rule/factor/fixed contract mismatch')
    return record


def validate_progress(progress):
    exact_keys(progress, ('completed_local_sweep','settling_sweeps','completed_production_sweeps',
                          'checkpoint_type','status'))
    for name in ('completed_local_sweep','settling_sweeps','completed_production_sweeps'):
        if type(progress[name]) is not int or progress[name] < 0:
            raise ValueError('Progress counts must be nonnegative integers')
    local = progress['completed_local_sweep']
    if (local < 1 or progress['completed_production_sweeps'] != max(0, local-progress['settling_sweeps'])
            or progress['checkpoint_type'] != 'complete' or progress['status'] != 'completed_sweep'):
        raise ValueError('Checkpoint is not a coherent completed sweep boundary')
    return parse_json(json_text(progress))
