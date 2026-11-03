"""Explicit child run from an authenticated completed parent; never exact-resume retuning."""
import copy
import jax
import numpy as np
from .checkpoint_contract import digest
from .checkpoint_rng import stream_audit
from .layer4 import state_hashes
from .run_controller import RunController
from .run_genesis import load_genesis
from .run_initialization import Endpoint, adapt
from .run_storage import file_record, read_json, writer


def parent_endpoint(parent):
    """Authenticate the complete immutable parent transaction chain under its lock."""
    if hasattr(parent, 'completed_endpoint'):
        return parent.completed_endpoint()
    with writer(parent.store.root):
        parent.authenticate()
        path = parent.store.segment/'genesis'
        genesis, logical = load_genesis(path/'endpoint.npz', parent.target, parent.cp)
        receipt = read_json(path/'receipt.json')
        expected_receipt = dict(schema='bsfm.genesis.v1',spec_sha256=parent.store.spec_hash,
            input_sha256=parent.spec['input_sha256'],endpoint=file_record(path/'endpoint.npz'),logical_sha256=logical)
        if receipt != expected_receipt:
            raise ValueError('Parent genesis file changed')
        chain = parent.store.scan(genesis, digest(receipt))
        n = len(chain['rows'])
        completion = read_json(parent.store.segment/'completion.json')
        if n != parent.spec['final_sweep'] or completion['head'] != chain['head'] or completion['completed'] != n:
            raise ValueError('Readaptation requires a complete authenticated parent')
        last = parent.store.segment/'transactions'/f'{n:012d}'
        binding = dict(schema='bsfm.readaptation-parent.v1',
            run_id=parent.spec['run_id'], segment_id=parent.spec['segment_id'],
            chain_id=parent.spec['chain_id'], spec_sha256=parent.store.spec_hash,
            head=chain['head'], completed_sweep=n,
            checkpoint=file_record(last/'checkpoint.npz'),
            checkpoint_logical_sha256=chain['endpoint'].logical_sha256,
            completion=file_record(parent.store.segment/'completion.json'),
            key_policy='split parent endpoint master key into next master and K ordered warmup keys; preserve NumPy streams',
            pooling='parent bridge draws excluded from child production')
        return copy.deepcopy(chain['endpoint']), binding


class ReadaptationController(RunController):
    def __init__(self, *args, parent, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        if self.store.root == parent.store.root or self.spec['run_id'] == parent.spec['run_id']:
            raise ValueError('Readaptation requires a separate child root and run ID')
        if self.target.identity != parent.target.identity or self.target.geometry.spectral_identity != parent.target.geometry.spectral_identity:
            raise ValueError('Readaptation cannot change target or spectral chart')
        if self.spec['seed'] != parent.spec['seed']:
            raise ValueError('Child retains seed lineage; streams are restored, not reseeded')
        _, expected = parent_endpoint(parent)
        if self.store.input_receipt.get('readaptation_parent') != expected:
            raise ValueError('Child does not bind exact completed parent')

    def _genesis(self, fault):
        endpoint, identity = super()._genesis(fault)
        if endpoint.evidence['initialization'].get('parent') != self.store.input_receipt['readaptation_parent']:
            raise ValueError('Retained child genesis changed parent binding')
        return endpoint, identity

    def _adapt_endpoint(self, fault):
        source, binding = parent_endpoint(self.parent)
        if self.store.input_receipt['readaptation_parent'] != binding:
            raise ValueError('Parent changed before child adaptation')
        if not np.array_equal(source.b_sigma2, self.scale):
            raise ValueError('Child changed fixed noise prior')
        keys = jax.random.split(source.master_key, len(self.target.factor_ids)+1)
        evidence = dict(schema='bsfm.readaptation-start.v1', seed=self.spec['seed'],
            parent=binding, state_after=state_hashes(source.state),
            warm_keys=[np.asarray(k).tolist() for k in keys[1:]],
            rng_parent=stream_audit(source.eta_rng, source.gauge_rng, source.master_key, source.numpy_global_state),
            rng_after=stream_audit(source.eta_rng, source.gauge_rng, keys[0], source.numpy_global_state))
        endpoint = Endpoint(source.state, source.positions, source.tuning, source.eta_rng,
            source.gauge_rng, keys[0], source.numpy_global_state, source.b_sigma2, evidence)
        fault('after_initialization')
        return adapt(self.target, endpoint, tuple(keys[1:]), steps=self.spec['warmup_steps'], split=self.layer.split)
