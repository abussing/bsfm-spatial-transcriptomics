"""Freeze user-selected L14 from two extracted members of the authenticated rule table."""
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from bsfm.sampler.contracts import logical_hash
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'sampler/s10-subset-smoke-20261103'))
from build_smoke_rule import construct

source=Path(sys.argv[1])
arrays=construct(np.load(source/'nodes_L14.npy',allow_pickle=False),np.load(source/'weights_L14.npy',allow_pickle=False),14)
record=dict(schema='bsfm.explicit-finite-rule.v1',order=14,ell_eta=.14,
    frequency_nodes=392,feature_columns=784,feature_order='all_cosine_then_all_sine_in_frequency_row_order',
    x64_required=True,scope='user-selected preliminary S10 holdout comparison; canonical L16 unchanged',
    table_sha256='5795086274dce8a27ac7f9220a5cd01f948de02a8f137f3af1a82148928c378d',
    construction='same audited tensor/sign pairing and normalization as L4 smoke; L16 construction comparison retained in smoke evidence',
    entries={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [source/'nodes_L14.npy',source/'weights_L14.npy']},
    logical_hashes={k:logical_hash(v) for k,v in arrays.items()},arrays={k:v.tolist() for k,v in arrays.items()})
dest=Path(__file__).with_name('L14_ell14.json');dest.write_bytes((json.dumps(record,indent=2)+'\n').encode())
print(hashlib.sha256(dest.read_bytes()).hexdigest())
