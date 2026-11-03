"""Bounded same-runtime historical comparison; no fixture rewriting or full driver execution."""
import argparse,hashlib,json,sys,time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();repo=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(repo/'src'),str(repo/'tests')]
import jax
import numpy as np
from threadpoolctl import threadpool_limits
from sampler_layer5_support import historical,gaussian_system,tree_record,evaluate
from sampler_layer6_support import authenticated_literal,run_case
from bsfm.sampler.split_kernels import build_split
assert jax.default_backend()=='cpu' and jax.config.x64_enabled
assert not a.output.exists()
receipt={'scope':'Synthetic same-runtime CPU lineage comparison; not GPU performance validation','checks':[]}
start=time.monotonic()
with threadpool_limits(limits=1):
    ref,sources=historical(a.sources);receipt['sources']=sources
    for steps in (50,100):
        old,args,_,_=gaussian_system(ref['build_split']);new,_,_,_=gaussian_system(build_split)
        r=old['adapt'](jax.random.PRNGKey(173),*args,steps)
        q=new['adapt'](jax.random.PRNGKey(173),*args,steps)
        exact=tree_record(r)==tree_record(q)
        receipt['checks'].append({'stage':'adaptation','steps':steps,'all_leaves_exact':exact})
    receipt['checks'].append({'stage':'layer5_gaussian_and_canonical_transition','exact':evaluate(ref)==evaluate()})
    literal,source=authenticated_literal(a.sources);receipt['driver']=source
    receipt['checks'].append({'stage':'layer6_literal_chronology_state_diagnostics_rng','exact':run_case(literal)==run_case()})
receipt['status']='PASS' if all(r.get('exact',r.get('all_leaves_exact')) for r in receipt['checks']) else 'FAIL'
receipt['elapsed_seconds']=time.monotonic()-start
receipt['environment']={'python':sys.version,'jax':jax.__version__,'numpy':np.__version__,'backend':jax.default_backend()}
receipt['source_hashes']={str(f.relative_to(repo)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (repo/'src/bsfm/sampler').glob('*.py')}
a.output.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_hashes','sources','driver']}),flush=True)
sys.exit(0 if receipt['status']=='PASS' else 1)
