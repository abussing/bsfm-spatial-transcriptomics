"""New run from a pinned pre-sweep endpoint; preserve all state and RNG streams."""
import numpy as np
from .checkpoint_contract import CheckpointContract
from .run_genesis import load_genesis
from .run_inputs import authenticate_files
from .run_periodic import PeriodicRunController
from .checkpoint_rng import parse_json


class ImportedEndpointController(PeriodicRunController):
    """Import completed tuning only, never a partially executed Gibbs sweep.

    The new run binds the original endpoint bytes and its embedded old software
    contract, and publishes a separate genesis under the new software contract.
    No source checkpoint is edited and no warmup or RNG draw is performed here.
    """
    def _adapt_endpoint(self, fault):
        record=self.store.input_receipt['initial_endpoint']
        authenticate_files({'initial_endpoint':record})
        with np.load(record['path'],allow_pickle=False) as z:
            metadata=parse_json(str(z['metadata']))
        contract=CheckpointContract(metadata['contract'],metadata['contract_sha256'])
        endpoint,_=load_genesis(record['path'],self.target,contract)
        evidence=endpoint.evidence
        if (evidence['adaptation_steps']!=self.spec['warmup_steps']
                or evidence['initialization']['seed']!=self.spec['seed']
                or not np.array_equal(endpoint.b_sigma2,self.scale)):
            raise ValueError('Imported tuning/seed/noise-prior mismatch')
        return endpoint
