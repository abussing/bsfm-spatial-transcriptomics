"""Explicit authenticated original-source comparison, saved small synthetic outputs."""
import argparse
import json
from pathlib import Path
from threadpoolctl import threadpool_limits
from sampler_layer3_support import system,historical,evaluate


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();ref,sources=historical(a.source_root);cases=[]
    with threadpool_limits(limits=1):
        for seed in (12,37):
            target,state,pos=system(seed);original=evaluate(target,state,pos,ref);port=evaluate(target,state,pos)
            if port!=original:raise AssertionError('Exact historical/port values, gradients, features or RNG comparison failed')
            cases.append(dict(seed=seed,expected=original))
    result=dict(schema='bsfm.sampler-layer3-fixture.v1',sources=sources,cases=cases,
                comparison='Exact same pinned CPU environment; feature matrix encoded by full logical hash',
                reference_scope='Authenticated original functions; only inactive containment import/construction removed; inactive alternative branches never executed')
    a.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print('PASS: two exact historical/port target, gradient, feature, eta and post-RNG fixtures')


if __name__=='__main__':main()
