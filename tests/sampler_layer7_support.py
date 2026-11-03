"""Tiny checkpoint fixtures and explicit synthetic run/software declarations."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import numpy as np
import jax

from bsfm.sampler.checkpoint import build_checkpoint_contract
from bsfm.sampler.checkpoint_contract import digest
from bsfm.sampler.layer6 import SweepResult, rng_audit
from bsfm.sampler.layer4 import state_hashes
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.conjugate import compute_Yhat
from sampler_layer6_support import fixture_system, ROOT

BASELINE = '164b0b1a6475805ebce3f0026f0ff58bd50f18c3'


def software():
    return dict(git_commit=BASELINE, clean_tree=False,
        run_config_sha256=digest(dict(purpose='synthetic checkpoint continuation', factors=2)),
        environment_lock_sha256=hashlib.sha256((ROOT/'environment/sampler-layer5/source-lock.json').read_bytes()).hexdigest(),
        environment_identity='sampler-layer5-cpu-20261102:Windows-CPU')


def contract_for(target, scale):
    declaration = software()
    return build_checkpoint_contract(target, b_sigma2=scale, software=declaration,
                                     expected_software_sha256=digest(declaration))


def progress(sweep=1, settling=0):
    return dict(completed_local_sweep=sweep, settling_sweeps=settling,
        completed_production_sweeps=max(0,sweep-settling), checkpoint_type='complete', status='completed_sweep')


def cheap_boundary(target, state, positions, key, scale, eta, gauge):
    """Construct a coherent synthetic I/O fixture, NOT evidence a sweep ran."""
    yhat=compute_Yhat(state.loading,state.eta,state.validate(target.inputs,factors=2))
    audit=dict(schema='bsfm.completed-sweep-audit.v1',factor_ids=list(target.factor_ids),
        state_after=state_hashes(state),positions_after=[logical_hash(p.values) for p in positions],
        target_sha256=hashlib.sha256(target.identity.encode()).hexdigest(),
        b_sigma2_sha256=logical_hash(scale),rng_after=rng_audit(eta,gauge,key),
        fitted_Y_sha256=logical_hash(yhat),label='synthetic-io-only')
    return SweepResult(copy.deepcopy(state),positions,key,(0,1),(),{},(),(),yhat,audit)


def tuning_record(tuning):
    return [dict(factor_id=t.factor_id,target_identity=t.target_identity,
        field_step=t.step_size,hyper_step=t.hyper_step_size,mass_sha256=logical_hash(t.inverse_mass_matrix),
        recorded_mass_sha256=t.mass_sha256) for t in tuning]


def all_hashes(result):
    from sampler_layer6_support import record_result
    data=record_result(result)
    return dict(logical_sha256=digest(data),audit_sha256=digest(result.audit),
                state=state_hashes(result.state),positions=[logical_hash(p.values) for p in result.positions],
                rng=result.audit['rng_after'],factor_order=list(result.factor_order))
