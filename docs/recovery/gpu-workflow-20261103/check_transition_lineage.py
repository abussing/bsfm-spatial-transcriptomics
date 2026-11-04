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
from sampler_layer3_support import historical as historical_target, system as target_system, evaluate as evaluate_target
assert jax.default_backend()=='cpu' and jax.config.x64_enabled
assert not a.output.exists()
receipt={'scope':'Synthetic same-runtime CPU lineage comparison; not GPU performance validation','checks':[]}
fixtures={name:repo/'tests/fixtures'/name for name in ('sampler_layer3.json','sampler_layer5.json')}
before={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in fixtures.items()}

def differences(actual, saved):
    """Describe exact failures, without changing an acceptance tolerance."""
    numeric=[];other=[]
    def walk(x,y,path):
        if isinstance(x,dict) and isinstance(y,dict) and x.keys()==y.keys():
            for k in x:walk(x[k],y[k],path+'/'+str(k))
        elif isinstance(x,list) and isinstance(y,list) and len(x)==len(y):
            for i,(v,w) in enumerate(zip(x,y)):walk(v,w,path+'/'+str(i))
        elif x!=y:
            if type(x) in (int,float) and type(y) in (int,float):
                numeric.append(dict(path=path,actual=x,saved=y,absolute_error=abs(x-y),
                    error_scaled_by_max_one_reference=abs(x-y)/max(1,abs(y))))
            else:other.append(path)
    walk(actual,saved,'')
    return dict(exact=actual==saved,numeric_mismatches=len(numeric),other_mismatches=len(other),
        max_absolute_error=max((x['absolute_error'] for x in numeric),default=0),
        max_error_scaled_by_max_one_reference=max((x['error_scaled_by_max_one_reference'] for x in numeric),default=0),
        largest_numeric_differences=sorted(numeric,key=lambda x:x['absolute_error'],reverse=True)[:10],
        other_paths=other[:30])
start=time.monotonic()
with threadpool_limits(limits=1):
    target_ref,target_sources=historical_target(a.sources)
    receipt['target_sources']=target_sources
    receipt['saved_fixture_comparisons']=[]
    for case in json.loads(fixtures['sampler_layer3.json'].read_text())['cases']:
        target,state,pos=target_system(case['seed'])
        old=evaluate_target(target,state,pos,target_ref);new=evaluate_target(target,state,pos)
        receipt['checks'].append(dict(stage='layer3_target_gradient_features_eta_rng',seed=case['seed'],exact=old==new))
        receipt['saved_fixture_comparisons'].append(dict(stage='layer3',seed=case['seed'],
            historical_vs_saved=differences(old,case['expected']),current_vs_saved=differences(new,case['expected'])))
    ref,sources=historical(a.sources);receipt['sources']=sources
    for steps in (50,100):
        old,args,_,_=gaussian_system(ref['build_split']);new,_,_,_=gaussian_system(build_split)
        r=old['adapt'](jax.random.PRNGKey(173),*args,steps)
        q=new['adapt'](jax.random.PRNGKey(173),*args,steps)
        exact=tree_record(r)==tree_record(q)
        receipt['checks'].append({'stage':'adaptation','steps':steps,'all_leaves_exact':exact})
    old,new=evaluate(ref),evaluate()
    receipt['checks'].append({'stage':'layer5_gaussian_and_canonical_transition','exact':old==new})
    saved=json.loads(fixtures['sampler_layer5.json'].read_text())['expected']
    receipt['saved_fixture_comparisons'].append(dict(stage='layer5',
        historical_vs_saved=differences(old,saved),current_vs_saved=differences(new,saved)))
    literal,source=authenticated_literal(a.sources);receipt['driver']=source
    receipt['checks'].append({'stage':'layer6_literal_chronology_state_diagnostics_rng','exact':run_case(literal)==run_case()})
receipt['status']='PASS' if all(r.get('exact',r.get('all_leaves_exact')) for r in receipt['checks']) else 'FAIL'
receipt['elapsed_seconds']=time.monotonic()-start
receipt['environment']={'python':sys.version,'jax':jax.__version__,'numpy':np.__version__,'backend':jax.default_backend()}
receipt['source_hashes']={str(f.relative_to(repo)):hashlib.sha256(f.read_bytes()).hexdigest() for f in (repo/'src/bsfm/sampler').glob('*.py')}
receipt['fixture_sha256']=before
receipt['fixtures_unchanged']=before=={name:hashlib.sha256(path.read_bytes()).hexdigest() for name,path in fixtures.items()}
assert receipt['fixtures_unchanged']
a.output.write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ['source_hashes','sources','driver']}),flush=True)
sys.exit(0 if receipt['status']=='PASS' else 1)
