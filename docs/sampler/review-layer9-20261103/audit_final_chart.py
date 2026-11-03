"""Revalidate retained synthetic genesis after the final modal-domain guard."""
import argparse,hashlib,json,sys,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tests')]
from sampler_layer9_support import controller
from bsfm.sampler.run_chart import geometry_from_genesis
from bsfm.sampler.field_target import DirectWTarget
from bsfm.sampler.run_genesis import load_genesis,boundary

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--genesis',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        c=controller(Path(tmp)/'unused');g=c.target.geometry
        original,_=load_genesis(args.genesis,c.target,c.cp)
        with patch('scipy.linalg.eigh',side_effect=AssertionError('Eigensystem recomputed')):
            restored=geometry_from_genesis(g.arrays,json.loads(g.identity_json),args.genesis)
            target=DirectWTarget(c.target.inputs,restored,c.target.rule,factor_ids=c.target.factor_ids)
            endpoint,_=load_genesis(args.genesis,target,c.cp)
        checks=dict(boundary_exact=boundary(original,c.target)==boundary(endpoint,target),
                    spectral_identity_exact=restored.spectral_identity==g.spectral_identity)
        result=dict(status='pass' if all(checks.values()) else 'fail',checks=checks,
            genesis_sha256=hashlib.sha256(args.genesis.read_bytes()).hexdigest(),
            chart_source_sha256=hashlib.sha256((ROOT/'src/bsfm/sampler/run_chart.py').read_bytes()).hexdigest(),
            scope='Existing authenticated synthetic genesis; no fresh warmup or scientific run')
        args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result))
        sys.exit(0 if all(checks.values()) else 1)
