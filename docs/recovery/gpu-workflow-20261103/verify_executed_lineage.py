"""Recheck captured lineage assertions and the current split-function comparison."""
import argparse,ast,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--historical-capture',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
a=p.parse_args();folder=Path(__file__).resolve().parent;repo=folder.parents[2]
r=json.loads((folder/'EXECUTED_LINEAGE.json').read_text())
s=json.loads((folder/'EXECUTION_SUPPLEMENT.json').read_text())
assert len(r['wasserstein_joins'])==11
assert all(x['draw_hash_matches'] and x['sweep_matches'] for x in r['wasserstein_joins'])
assert len(r['kernel_comparisons'])==9
assert all(x['identical'] and x['split_manifest_matches'] for x in r['kernel_comparisons'])
assert r['split_gate_manifest_matches']
assert len(s['run_code_manifest_joins'])==11
assert all(x['matches_selected_driver'] for x in s['run_code_manifest_joins'])
assert s['gpu_validation']['status']=='PASS'
capture=json.loads(a.historical_capture.read_text())
record=next(v for k,v in capture.items() if k.endswith('/full_split.py'))
assert hashlib.sha256(record['text'].encode()).hexdigest()==record['sha256']
assert record['sha256']=='f2b26f954d49dc51dfa542874df0de87936698db7714fca907292a7c495b06cd'
current=repo/'src/bsfm/sampler/split_kernels.py'
def get(text):
    return next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name=='build_split')
old=get(record['text']);new=get(current.read_text());removed=[]
for node in ast.walk(new):
    if isinstance(node,ast.FunctionDef) and node.name=='one':
        for v in node.body:
            if isinstance(v,ast.If) and ast.unparse(v.test)=="jax.default_backend() == 'gpu'":
                assert ast.unparse(v.body[0])=='ac = gpu_acceptance_roundoff(ac)' and len(v.body)==1 and not v.orelse
                removed.append(v)
        node.body=[v for v in node.body if v not in removed]
assert len(removed)==1
assert ast.dump(old,include_attributes=False)==ast.dump(new,include_attributes=False)
out=dict(status='PASS',scope='Recheck captured provenance assertions and current source AST; not a fresh historical run',
    draw_joins=11,code_manifest_joins=11,identical_kernel_files=9,
    current_split_ast_exact_except_documented_gpu_roundoff_guard=True,
    current_source_sha256=hashlib.sha256(current.read_bytes()).hexdigest(),
    historical_split_sha256=record['sha256'])
a.output.write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
