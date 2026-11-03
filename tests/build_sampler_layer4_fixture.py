"""Explicit bounded reference evaluation; ordinary tests use saved fixtures."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from threadpoolctl import threadpool_limits
from sampler_layer4_support import ROOT, FUNCTIONS, historical, evaluate
from sampler_provenance import body_ast_sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();ref,sources=historical(args.source_root);cases=[]
    with threadpool_limits(limits=1):
        for seed in (12,37):
            expected=evaluate(seed,ref);actual=evaluate(seed)
            if actual!=expected:raise AssertionError('Exact Layer-4 historical/port comparison failed')
            cases.append(dict(seed=seed,expected=expected))
    args.output.write_text(json.dumps(dict(schema='bsfm.sampler-layer4-fixture.v1',sources=sources,
        cases=cases,comparison='Exact same accepted CPU environment; canonical beta arrays stored as ordered logical hashes; small beta arrays explicit'),
        indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    rows=[]
    for source in sources:
        source_path=Path(source['path']);text=source_path.read_text();lines=text.splitlines()
        port_file,names=FUNCTIONS[source_path.name];port_path=Path('src/bsfm/sampler')/port_file
        port_bytes=(ROOT/port_path).read_bytes()
        originals={n.name:n for n in ast.parse(text).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        ports={n.name:n for n in ast.parse(port_bytes).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        for name in names:
            a=originals[name];b=ports[name];ha=body_ast_sha256(a);hb=body_ast_sha256(b)
            assert ha==hb,name
            rows.append(dict(source_path=source['path'],source_bytes=source['bytes'],source_sha256=source['sha256'],
                source_function=name,source_start=a.lineno,source_end=a.end_lineno,
                source_fragment_sha256=hashlib.sha256(('\n'.join(lines[a.lineno-1:a.end_lineno])+'\n').encode()).hexdigest(),
                source_body_ast_sha256=ha,port_path=port_path.as_posix(),port_function=name,
                port_start=b.lineno,port_end=b.end_lineno,port_body_ast_sha256=hb,body_ast_exact=True,
                port_file_sha256=hashlib.sha256(port_bytes).hexdigest()))
    with (ROOT/'docs/sampler/LAYER4_SOURCE_MAP.csv').open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    print('PASS: two exact target/gradient/whitening/joint-draw/diagnostic/RNG fixtures; 12 exact source bodies')


if __name__=='__main__':main()
