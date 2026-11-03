"""Freeze smoke-only L4 from authenticated entries; record L16 construction comparison."""
import hashlib
import itertools
import json
from pathlib import Path
import sys
import numpy as np
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.rule import load_rule


def construct(nodes, weights, order):
    assert nodes.shape == weights.shape == (order,)
    signed_nodes = np.concatenate((nodes, -nodes))
    signed_weights = np.concatenate((weights, weights))*0.5
    signed_weights *= 1.15/np.sqrt(np.pi)
    all_nodes = np.asarray(list(itertools.product(signed_nodes, signed_nodes)), dtype=np.float64)
    all_weights = np.asarray(list(itertools.product(signed_weights, signed_weights)), dtype=np.float64).prod(axis=1)
    seen, keep = set(), []
    for index, node in enumerate(all_nodes):
        if tuple(-node) not in seen:
            keep.append(index)
        seen.add(tuple(node))
    weights = 2.0*all_weights[keep]
    weights /= np.sum(weights)
    omega = (2.0*np.sqrt(2.0)*1.15/float(.14))*all_nodes[keep]
    return dict(omega=omega, weights=weights, sqrt_weights=np.sqrt(weights))


if __name__ == '__main__':
    source = Path(sys.argv[1])
    def rule(order):
        return construct(np.load(source/f'nodes_L{order}.npy', allow_pickle=False),
                         np.load(source/f'weights_L{order}.npy', allow_pickle=False), order)
    canonical = load_rule()
    rebuilt = rule(16)
    assert all(np.array_equal(rebuilt[k], canonical.arrays[k]) for k in ('weights','sqrt_weights'))
    np.testing.assert_allclose(rebuilt['omega'],canonical.arrays['omega'],rtol=4*np.finfo(float).eps,atol=0)
    arrays = rule(4)
    record = dict(schema='bsfm.smoke-only-L4-rule.v1', order=4, ell_eta=.14,
        frequency_nodes=32, feature_columns=64,
        feature_order='all_cosine_then_all_sine_in_frequency_row_order',
        x64_required=True, scientific_use_approved=False,
        table_sha256='5795086274dce8a27ac7f9220a5cd01f948de02a8f137f3af1a82148928c378d',
        table_path='/work/abussing/arka_trying_gpu_again/helmholtz_c3full_n4500_bank10_v1/official_tqff_gamma115_orders_2_1099.npz',
        construction_source_path='/work/abussing/arka_trying_gpu_again/fixed_precision27_n2500_direct_L16_v1/tqff_se_features.py',
        construction_source_sha256=hashlib.sha256((source/'tqff_se_features.py').read_bytes()).hexdigest(),
        canonical_L16_comparison=dict(weights_exact=True,sqrt_weights_exact=True,
            frequency_max_absolute_difference=float(np.max(abs(rebuilt['omega']-canonical.arrays['omega']))),
            frequency_exact=bool(np.array_equal(rebuilt['omega'],canonical.arrays['omega'])),
            note='Construction comparison only; canonical L16 bytes and accepted test thresholds are unchanged'),
        extracted_entries={p.name:dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(source.glob('*.npy'))},
        logical_hashes={k:logical_hash(v) for k,v in arrays.items()},
        arrays={k:v.tolist() for k,v in arrays.items()})
    path=Path(__file__).with_name('L4_ell14_smoke.json')
    path.write_bytes((json.dumps(record,indent=2,allow_nan=False)+'\n').encode())
    print('L16 construction comparison recorded; L4 frozen:',hashlib.sha256(path.read_bytes()).hexdigest())
