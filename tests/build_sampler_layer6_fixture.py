"""Authenticate selected driver statements and freeze one synthetic sweep."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
from threadpoolctl import threadpool_limits
from sampler_layer6_support import authenticated_literal,run_case


def source_map(source, destination):
    root=Path(__file__).resolve().parents[1]
    path=root/'src/bsfm/sampler/layer6.py';data=path.read_bytes();lines=data.decode().splitlines()
    original=Path(source['path']).read_text(encoding='utf-8').splitlines()
    methods={n.name:n for n in ast.walk(ast.parse(data)) if isinstance(n,ast.FunctionDef)}
    def line(text,start=0):return next(i+1 for i in range(start,len(lines)) if text in lines[i])
    specs=[
        ('constants',41,51,line('N_INNER ='),line('ELL_ETA ='),'Reuse approved Layer-1 prior constants; no new choices'),
        ('fixed_noise_prior',494,496,methods['__init__'].lineno,methods['__init__'].end_lineno,'Caller supplies initialization scale; never re-estimate in sweep'),
        ('three_Lambda_updates',1121,1125,line('for _inner in'),line('sharing, cell_slices)'),'Exactly three accepted conjugate calls'),
        ('features_joint_eta',1127,1143,methods['_joint_eta'].lineno,methods['_joint_eta'].end_lineno,'Public Layer-4 joint draw rebuilds all features; unchanged PCG contract'),
        ('fitted_noise',1145,1146,line('yhat = compute_Yhat'),line('SIGMA2_PRIOR_SHAPE, self._b_sigma2)'),'Fitted values then supplied-scale noise draw'),
        ('q_phi',1150,1154,line('qgk = compute_qgk'),line('a_phi=contracts.A_PHI'),'Selected shrinkage branch only'),
        ('delta_tau',1156,1162,line('work.delta, work.tau ='),line('a_delta1=contracts.A_DELTA1'),'Selected sequential delta/tau branch only'),
        ('PX_positions_fitted',1164,1172,line('work.loading, work.eta, work.alpha, gauge ='),line('yhat = compute_Yhat',line('current[i].values[0]')),'Accepted PX then log-alpha chart and fitted values'),
        ('random_order',1179,1181,line('order = tuple'),line('order = tuple'),'Global NumPy permutation; factor labels unchanged'),
        ('context_key_split',1182,1188,line('context = self.split.prepare_context'),line('master_key, step_key ='),'Fresh context before exact master/step split'),
        ('split_transition',1189,1200,line('result = self.split.transition'),line('state_factor_ids=target.factor_ids, prepared_context=context)'),'Public Layer-5 prepared transition; shared exact chart boundary'),
        ('chart_hypers',1201,1216,line('current[i] = result.position'),line('jnp.asarray(p[3])'),'Source alpha/zeta and coupled warp parameters; fixed ell_eta'),
        ('single_eta_fitted',1263,1270,line('work.eta[i], eta_audit ='),line('yhat = compute_Yhat',line('work.eta[i], eta_audit =')),'One Layer-3 draw immediately followed by fitted values')]
    rows=[]
    for stage,a,b,c,d,treatment in specs:
        rows.append(dict(stage=stage,source_path=source['path'],source_bytes=source['bytes'],source_sha256=source['sha256'],source_start=a,source_end=b,
            source_fragment_sha256=hashlib.sha256(('\n'.join(original[a-1:b])+'\n').encode()).hexdigest(),
            port_path=path.relative_to(root).as_posix(),port_start=c,port_end=d,
            port_file_sha256=hashlib.sha256(data).hexdigest(),treatment=treatment))
    with destination.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();code,source=authenticated_literal(args.source_root)
    with threadpool_limits(limits=1):
        expected=run_case(code);actual=run_case()
    if actual!=expected:
        differing=[k for k in actual if actual[k]!=expected[k]]
        args.output.with_suffix('.failure.json').write_text(json.dumps(dict(differing=differing,expected=expected,actual=actual),indent=2)+'\n',encoding='utf-8',newline='\n')
        raise AssertionError('Literal/canonical sweep differs: '+str(differing))
    record=dict(schema='bsfm.sampler-layer6-fixture.v1',source=source,
        seeds=dict(numpy_global=491,eta_generator=193,gauge_generator=307,jax_master=419),
        synthetic_dimensions=dict(cells=3,genes=2,types=3,factors=2,active_vertices=3,features=1024),
        expected=expected,comparison='exact same-environment literal chronology versus canonical composition')
    args.output.write_text(json.dumps(record,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    source_map(source,Path(__file__).resolve().parents[1]/'docs/sampler/LAYER6_SOURCE_MAP.csv')
    print('PASS: exact complete-sweep state, positions, diagnostics, order, fitted Y and all four RNG streams')


if __name__=='__main__':main()
