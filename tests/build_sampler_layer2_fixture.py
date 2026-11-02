"""Explicit bounded historical comparisons; normal tests never need legacy files."""
import argparse
import json
import platform
from pathlib import Path
import numpy as np
import scipy
import jax
from threadpoolctl import threadpool_limits
from sampler_layer2_support import historical_reference, synthetic, evaluate, port_functions, serial


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();ref,sources=historical_reference(args.source_root)
    cases=[]
    with threadpool_limits(limits=1):
        for scale,ell in [(1.,.3),(.7,1.)]:
            data=synthetic(scale);expected=serial(evaluate(ref,data,float(np.log(ell))))
            actual=serial(evaluate(port_functions(),data,float(np.log(ell))))
            if actual!=expected:raise AssertionError('Historical/port exact comparison failed')
            cases.append(dict(scale=scale,ell=ell,expected=expected))
    result=dict(schema='bsfm.sampler-layer2-regression.v1',sources=sources,cases=cases,
                comparison='exact same CPU environment, all recorded arrays and diagnostics',
                python=platform.python_version(),numpy=np.__version__,scipy=scipy.__version__,
                jax=jax.__version__,backend=jax.default_backend(),x64=jax.config.x64_enabled)
    args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print('PASS: 2 exact same-environment historical/port FEM fixtures')


if __name__=='__main__':main()
