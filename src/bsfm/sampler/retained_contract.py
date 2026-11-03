"""Retained inference identities and explicit storage cadence; no run defaults."""
from dataclasses import dataclass
from .checkpoint_contract import (build_checkpoint_contract, validate_contract,
                                  CheckpointContract, digest)
from .checkpoint_rng import json_text, parse_json, exact_keys

SCHEMA = 'bsfm.retained-archive.v1'
RECORD_SCHEMA = 'bsfm.retained-record.v1'


def count(x, name, minimum=0):
    if type(x) is not int or x < minimum:
        raise ValueError(name+' must be an explicit integer')
    return x


@dataclass(frozen=True)
class RetainedContract:
    json: str
    sha256: str


def build_retained_contract(target, *, b_sigma2, software, expected_software_sha256,
                            chain_id, save_every, settling_sweeps, final_sweep):
    if not isinstance(chain_id, str) or not chain_id:
        raise ValueError('Explicit chain identity required')
    count(save_every, 'save_every', 1)
    count(settling_sweeps, 'settling_sweeps')
    if final_sweep is not None:
        count(final_sweep, 'final_sweep', settling_sweeps+1)
    base = build_checkpoint_contract(target, b_sigma2=b_sigma2, software=software,
                                    expected_software_sha256=expected_software_sha256)
    record = dict(schema=SCHEMA, chain_id=chain_id, continuation_contract=parse_json(base.json),
                  continuation_sha256=base.sha256, retention=dict(save_every=save_every,
                  settling_sweeps=settling_sweeps, final_sweep=final_sweep,
                  rule='post_settling_and_first_or_modulo_or_final'))
    return RetainedContract(json_text(record), digest(record))


def validate_retained_contract(contract, target, b_sigma2):
    if not isinstance(contract, RetainedContract):
        raise ValueError('Expected retained contract required')
    r = parse_json(contract.json)
    exact_keys(r, ('schema','chain_id','continuation_contract','continuation_sha256','retention'))
    exact_keys(r['retention'], ('save_every','settling_sweeps','final_sweep','rule'))
    if contract.sha256 != digest(r) or contract.json != json_text(r):
        raise ValueError('Retained contract mutated')
    base = CheckpointContract(json_text(r['continuation_contract']), r['continuation_sha256'])
    validate_contract(base, target, b_sigma2)
    expected = build_retained_contract(target, b_sigma2=b_sigma2,
        software=r['continuation_contract']['software'],
        expected_software_sha256=r['continuation_contract']['software_sha256'],
        chain_id=r['chain_id'], **{k:r['retention'][k] for k in ('save_every','settling_sweeps','final_sweep')})
    if expected != contract:
        raise ValueError('Incompatible retained contract')
    return r


def retain_at(contract_record, sweep):
    count(sweep, 'sweep', 1)
    p = contract_record['retention']
    if p['final_sweep'] is not None and sweep > p['final_sweep']:
        raise ValueError('Beyond declared final sweep')
    return sweep > p['settling_sweeps'] and (
        sweep == 1 or sweep % p['save_every'] == 0 or sweep == p['final_sweep'])
