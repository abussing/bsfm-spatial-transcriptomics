"""Bounded historical warmup statements vs a retained synthetic genesis.

No monolith import, fixture rewrite, scientific inputs, or tolerance waiver.
Accepted Layer-5 kernels supply the numerical transition; the selected original
driver statements independently compose contexts, endpoints and eta draws.
"""
import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile

REPO=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(REPO/'src'),str(REPO/'tests')]
import jax
import numpy as np
from bsfm.sampler.contracts import GaussianState,logical_hash
from bsfm.sampler.factor_statistics import factor_context,sample_single_eta
from bsfm.sampler.layer4 import STATE_ARRAYS,state_hashes
from bsfm.sampler.run_genesis import load_genesis,boundary
from bsfm.sampler.checkpoint_rng import stream_audit
from bsfm.sampler.retained_diagnostics import encode
from sampler_layer9_support import controller,literal_initialization

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--historical-driver',type=Path,required=True)
    ap.add_argument('--genesis',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    os.environ['BSFM_HISTORICAL_DRIVER']=str(args.historical_driver)
    with tempfile.TemporaryDirectory() as tmp:
        c=controller(Path(tmp)/'unused')
        expected,_=load_genesis(args.genesis,c.target,c.cp)
        ns,source=literal_initialization(c.target,c.loading,c.eta,491)
        tree=ast.parse(args.historical_driver.read_bytes())
        def at(line):
            return copy.deepcopy(next(n for n in ast.walk(tree)
                if isinstance(n,ast.stmt) and n.lineno==line))
        prefix=(675,676,677,678,682,693)
        inner=(700,701,704,712,734,906,907,908,909,910,924)
        suffix=(942,943,944,945,946)
        loop=at(697);loop.body=[at(n) for n in inner]
        loop.body+=ast.parse('reference_histories.append(warmup_history)').body
        module=ast.fix_missing_locations(ast.Module(
            body=[at(n) for n in prefix]+[loop]+[at(n) for n in suffix],type_ignores=[]))
        ns.update(restarting=False,readapting=False,resume_tuning=[],
            factor_context=factor_context,sample_single_eta=sample_single_eta,
            cell_id=c.target.inputs.arrays['cell_id'],
            split_runners=[c.layer.split._runner]*len(c.target.factor_ids),
            targets=[c.target._kernels]*len(c.target.factor_ids),reference_histories=[])
        ns['args'].warmup=20
        exec(compile(module,str(args.historical_driver),'exec'),ns)
        state=GaussianState(**{n:ns[n] for n in STATE_ARRAYS},input_identity_json=c.target.inputs.identity_json)
        checks=dict(state=state_hashes(state)==state_hashes(expected.state),
            positions=[logical_hash(np.asarray(p)) for p in ns['positions']]==[logical_hash(p.values) for p in expected.positions],
            rng=stream_audit(ns['rng'],ns['gauge_rng'],ns['master_key'],np.random.get_state())==boundary(expected,c.target)['rng_after'],
            histories=[encode(h) for h in ns['reference_histories']]==[r['history'] for r in expected.evidence['factors']],
            tuning=all(float(raw['step_size'])==t.step_size and float(raw['hyper_step_size'])==t.hyper_step_size
                and np.array_equal(np.asarray(raw['inverse_mass_matrix']),t.inverse_mass_matrix)
                for raw,t in zip(ns['parameters'],expected.tuning)))
        result=dict(status='pass' if all(checks.values()) else 'not_passed',checks=checks,
            source=source,prefix_lines=prefix,loop_lines=inner,suffix_lines=suffix,
            selected_AST_sha256=hashlib.sha256(ast.dump(module,include_attributes=False).encode()).hexdigest(),
            genesis_sha256=hashlib.sha256(args.genesis.read_bytes()).hexdigest(),target_acceptance=.9,
            warmup_steps=20,scope='Independent historical composition using accepted Layer-5 kernels; synthetic only')
        args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(checks),flush=True)
        if not all(checks.values()):raise AssertionError('Historical warmup composition differs')

if __name__=='__main__':main()
