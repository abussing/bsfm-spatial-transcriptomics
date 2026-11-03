"""Explicit selected-source regression acquisition; not a scientific run."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from threadpoolctl import threadpool_limits
from sampler_layer5_support import ROOT, historical, evaluate
from sampler_provenance import body_ast_sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference, sources = historical(args.source_root)
    with threadpool_limits(limits=1):
        expected = evaluate(reference)
        actual = evaluate()
    if expected != actual:
        raise AssertionError('Exact source/port Layer-5 comparison failed')
    args.output.write_text(json.dumps(dict(schema='bsfm.sampler-layer5-fixture.v1',
        sources=sources, expected=expected), indent=2, allow_nan=False)+'\n', encoding='utf-8', newline='\n')
    port = ROOT/'src/bsfm/sampler/split_kernels.py'; pb=port.read_bytes()
    pn = {n.name:n for n in ast.parse(pb).body if isinstance(n, ast.FunctionDef)}
    rows=[]
    for source, name in zip(sources, ['build_split', 'make_logdensity']):
        text=Path(source['path']).read_text(encoding='utf-8')
        n=next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name==name)
        p=pn[name]; a=body_ast_sha256(n); b=body_ast_sha256(p); assert a==b
        rows.append(dict(source_path=source['path'],source_bytes=source['bytes'],source_sha256=source['sha256'],
            source_function=name,source_start=n.lineno,source_end=n.end_lineno,
            source_fragment_sha256=hashlib.sha256(('\n'.join(text.splitlines()[n.lineno-1:n.end_lineno])+'\n').encode()).hexdigest(),
            source_body_ast_sha256=a,port_path=port.relative_to(ROOT).as_posix(),port_function=name,
            port_start=p.lineno,port_end=p.end_lineno,port_body_ast_sha256=b,body_ast_exact=True,
            port_file_sha256=hashlib.sha256(pb).hexdigest()))
    with (ROOT/'docs/sampler/LAYER5_SOURCE_MAP.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print('PASS: exact source/port transition, adaptation, diagnostics, histories and key behavior')


if __name__=='__main__': main()
