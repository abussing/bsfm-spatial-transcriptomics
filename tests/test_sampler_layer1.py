"""Exact selected-source fixtures plus independent contract/PX rejection checks."""
import ast
import copy
import csv
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import numpy as np
from threadpoolctl import threadpool_limits

from bsfm.sampler import contracts as ct, conjugate as cg, shrinkage as sh, px
from build_sampler_layer1_fixture import evaluate, port_functions, rng_hash

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads((ROOT/'tests/fixtures/sampler_layer1.json').read_text(encoding='utf-8'))


def data_and_state():
    case = FIXTURE['cases'][1]
    d = {k: np.array(v, dtype=np.float64) for k, v in case['inputs'].items() if k != 'counts'}
    counts = case['inputs']['counts']; c, g, k = d['loading'].shape; n = d['Y'].shape[1]
    data = dict(Y=d['Y'].copy(), slocs=np.column_stack((np.arange(n)*.03, np.arange(n)*.07)),
                cell_id=np.repeat(np.arange(c, dtype=np.int64), counts),
                cell_names=np.array([f'cell-{i}' for i in range(n)]),
                source_row_indices=np.arange(n, dtype=np.int64)*2,
                gene_names=np.array([f'gene-{i}' for i in range(g)]),
                cell_type_names=np.array(['MIC', 'AST', 'OGC']))
    identity = ct.input_identity(data, section='synthetic', response_sha256='a'*64,
                                 coordinate_system='october26_glial_min_max_span')
    inputs = ct.ModelInput.authenticate(data, identity)
    state = ct.GaussianState(d['loading'], d['eta'], d['alpha'], np.full(k,.5),
        d['sigma2'], d['phi'], d['delta'], d['tau'], inputs.identity_json)
    return data, identity, inputs, state


class ExactRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with threadpool_limits(limits=1):
            cls.outputs = [evaluate(port_functions(), c['inputs'], c['seed'], c['order'])
                           for c in FIXTURE['cases']]

    def compare(self, *keys):
        for case, actual in zip(FIXTURE['cases'], self.outputs):
            for key in keys:
                with self.subTest(seed=case['seed'], key=key):
                    self.assertEqual(actual[key], case['expected'][key])

    def test_fitted_values_exact(self):
        self.compare('Yhat', 'updated_Yhat')

    def test_qgk_exact(self):
        self.compare('qgk')

    def test_loading_draw_exact(self):
        self.compare('Lambda')

    def test_noise_draw_exact(self):
        self.compare('sigma2')

    def test_phi_draw_exact(self):
        self.compare('phi')

    def test_delta_tau_draw_exact(self):
        self.compare('delta', 'tau')

    def test_px_draw_and_audit_exact(self):
        self.compare('px_loading', 'px_eta', 'px_alpha', 'px_audit')

    def test_both_rng_streams_advance_exactly(self):
        self.compare('global_rng_sha256', 'px_rng_state')

    def test_repeated_execution_exact(self):
        with threadpool_limits(limits=1):
            for case, first in zip(FIXTURE['cases'], self.outputs):
                self.assertEqual(evaluate(port_functions(), case['inputs'], case['seed'], case['order']), first)

    def test_scalar_reference_qgk(self):
        _, _, _, state = data_and_state()
        c, g, k = state.loading.shape
        inv = np.linalg.inv(.8*np.eye(c)+.2*np.ones((c,c)))
        expected = np.array([[state.loading[:,i,j] @ inv @ state.loading[:,i,j]
                              for j in range(k)] for i in range(g)])
        np.testing.assert_allclose(sh.compute_qgk(state.loading,np.full(k,.2),c), expected,
                                   rtol=2e-15, atol=0)

    def test_independent_px_invariants(self):
        for case, output in zip(FIXTURE['cases'], self.outputs):
            lam = np.array(output['Lambda']); eta = np.array(case['inputs']['eta'])
            alpha = np.array(case['inputs']['alpha']); k = len(alpha)
            pl, pe, pa = [np.array(output[key]) for key in ('px_loading','px_eta','px_alpha')]
            counts=case['inputs']['counts']; stops=np.cumsum(counts)
            slices=[slice(int(a),int(b)) for a,b in zip(np.r_[0,stops[:-1]],stops)]
            pairs=[(cg.compute_Yhat(pl,pe,slices),cg.compute_Yhat(lam,eta,slices)),
                   (pl*pa[None,None,:],lam*alpha[None,None,:]),
                   (pe/pa[:,None],eta/alpha[:,None]),
                   (sh.compute_qgk(pl,np.full(k,.2),len(counts))*pa[None,:]**2,
                    sh.compute_qgk(lam,np.full(k,.2),len(counts))*alpha[None,:]**2)]
            for left,right in pairs:
                self.assertLessEqual(np.max(np.abs(left-right))/max(1.,np.max(np.abs(right))),5e-13)

    def test_px_guard_detects_broken_quadratic(self):
        _,_,_,s=data_and_state();original=px.compute_qgk;calls=0
        def altered(*args):
            nonlocal calls
            calls+=1
            return original(*args)*(1.1 if calls==2 else 1.)
        with patch.object(px,'compute_qgk',side_effect=altered):
            with self.assertRaises(RuntimeError):
                px.refresh_alpha_gauge(s.loading,s.eta,s.alpha,np.random.default_rng(4),np.full(2,.2),'mutant')

    def test_selected_delta_default_matches_explicit_override(self):
        _,_,_,s=data_and_state();q=sh.compute_qgk(s.loading,np.full(2,.2),3)
        saved=np.random.get_state()
        try:
            np.random.seed(19);a=sh.sample_delta_tau(q,s.alpha,s.phi,s.delta,2,3,4)
            np.random.seed(19);b=sh.sample_delta_tau(q,s.alpha,s.phi,s.delta,2,3,4,2.1,1.5)
            for x,y in zip(a,b):np.testing.assert_array_equal(x,y)
            with self.assertRaises(ValueError):sh.sample_delta_tau(q,s.alpha,s.phi,s.delta,2,3,4,2.1,3.1)
        finally:np.random.set_state(saved)

    def test_port_math_ast_matches_source_record(self):
        with (ROOT/'docs/sampler/LAYER1_SOURCE_MAP.csv').open(encoding='utf-8') as stream:
            rows=list(csv.DictReader(stream))
        self.assertEqual(len(rows),7)
        for row in rows:
            text=(ROOT/row['port_path']).read_text(encoding='utf-8')
            node=next(n for n in ast.parse(text).body if isinstance(n,ast.FunctionDef) and n.name==row['function'])
            self.assertEqual((node.lineno,node.end_lineno),(int(row['port_start']),int(row['port_end'])))
            body=[]
            for n in node.body:
                if isinstance(n,ast.Expr):
                    if isinstance(n.value,ast.Constant) and isinstance(n.value.value,str):continue
                    if isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='contracts':continue
                body.append(n)
            digest=hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False).encode()).hexdigest()
            self.assertEqual(digest,row['mathematical_body_ast_sha256'])


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.data,self.identity,self.inputs,self.state=data_and_state()
        self.slices=self.state.validate(self.inputs,factors=2)

    def test_complete_valid_layer_contract(self):
        self.assertEqual(self.slices,(slice(0,2),slice(2,6),slice(6,12)))
        self.assertEqual(json.loads(self.inputs.identity_json)['units'],'normalized')
        self.assertEqual(self.data['Y'].shape,(4,12))

    def test_no_input_aliasing_or_writes(self):
        expected=self.data['Y'].copy();self.data['Y'][0,0]+=1
        np.testing.assert_array_equal(self.inputs.arrays['Y'],expected)
        with self.assertRaises(ValueError):self.inputs.arrays['Y'][0,0]=0
        with self.assertRaises(TypeError):self.inputs.arrays['Y']=expected

    def test_deliberate_input_mutation_detected(self):
        a=self.inputs.arrays['Y'];a.flags.writeable=True;a[0,0]+=1
        with self.assertRaises(ValueError):self.inputs.validate()

    def test_response_and_coordinate_corruption(self):
        for field in ['Y','slocs']:
            with self.subTest(field=field):
                d=copy.deepcopy(self.data);d[field].flat[0]+=1e-10
                with self.assertRaises(ValueError):ct.ModelInput.authenticate(d,self.identity)

    def test_order_and_identity_corruption(self):
        for field in ['gene_names','cell_names','cell_type_names','source_row_indices','cell_id']:
            with self.subTest(field=field):
                d=copy.deepcopy(self.data);d[field]=d[field][::-1].copy()
                with self.assertRaises(ValueError):ct.ModelInput.authenticate(d,self.identity)

    def test_bad_manifest_fields(self):
        for key,value in [('schema','wrong'),('response','smoothed'),('axis_order',['center_x','center_y']),
                          ('units','microns'),('response_sha256','invalid'),('coordinate_system','guess')]:
            with self.subTest(key=key):
                identity=copy.deepcopy(self.identity);identity[key]=value
                with self.assertRaises(ValueError):ct.ModelInput.authenticate(self.data,identity)
        with self.assertRaises(ValueError):ct.ModelInput.authenticate(self.data,{})

    def test_duplicates_missing_and_object_ids(self):
        for field in ['gene_names','cell_names','source_row_indices','cell_type_names']:
            d=copy.deepcopy(self.data);d[field][1]=d[field][0]
            with self.assertRaises(ValueError):ct.validate_input(d)
        d=copy.deepcopy(self.data);del d['gene_names']
        with self.assertRaises(ValueError):ct.validate_input(d)
        d=copy.deepcopy(self.data);d['cell_names']=d['cell_names'].astype(object)
        with self.assertRaises(ValueError):ct.validate_input(d)

    def test_bad_input_shapes_finiteness_and_codes(self):
        for key,value in [('Y',np.zeros((4,0))),('slocs',np.zeros((12,3))),
                           ('cell_id',np.full(12,3,dtype=np.int64)),
                           ('cell_id',np.zeros(12,dtype=np.int64)),
                           ('source_row_indices',np.arange(12,dtype=float))]:
            d=copy.deepcopy(self.data);d[key]=value
            with self.assertRaises(ValueError):ct.validate_input(d)
        for field in ['Y','slocs']:
            for value in [np.inf,np.nan]:
                d=copy.deepcopy(self.data);d[field].flat[0]=value
                with self.assertRaises(ValueError):ct.validate_input(d)

    def test_state_requires_same_input_and_explicit_K(self):
        self.state.input_identity_json='{}'
        with self.assertRaises(ValueError):self.state.validate(self.inputs,factors=2)
        self.state.input_identity_json=self.inputs.identity_json
        for k in [0,-1,True,2.0,3]:
            with self.assertRaises(ValueError):self.state.validate(self.inputs,factors=k)

    def test_state_domains_shapes_and_tau(self):
        for field in ['loading','eta','alpha','zeta','sigma2','phi','delta','tau']:
            for mutation in ['shape','nan']:
                s=copy.deepcopy(self.state)
                if mutation=='shape':setattr(s,field,getattr(s,field).ravel()[:1])
                else:getattr(s,field).flat[0]=np.nan
                with self.subTest(field=field,mutation=mutation):
                    with self.assertRaises(ValueError):s.validate(self.inputs,factors=2)
        for field in ['alpha','sigma2','phi','delta','tau','zeta']:
            s=copy.deepcopy(self.state);getattr(s,field).flat[0]=0
            with self.assertRaises(ValueError):s.validate(self.inputs,factors=2)
        s=copy.deepcopy(self.state);s.zeta[0]=1
        with self.assertRaises(ValueError):s.validate(self.inputs,factors=2)
        s=copy.deepcopy(self.state);s.tau[0]+=1e-10
        with self.assertRaises(ValueError):s.validate(self.inputs,factors=2)

    def test_invalid_slices_rejected(self):
        for slices in [[slice(0,2),slice(1,6),slice(6,12)],
                       [slice(0,2),slice(2,6),slice(6,11)],
                       [slice(0,2,2),slice(2,6),slice(6,12)],
                       [slice(0,0),slice(0,6),slice(6,12)], []]:
            with self.assertRaises(ValueError):cg.compute_Yhat(self.state.loading,self.state.eta,slices)

    def test_malformed_calls_reject_before_random_draws(self):
        s=self.state;q=sh.compute_qgk(s.loading,np.full(2,.2),3)
        bads=[lambda:sh.compute_qgk(s.loading,np.full(2,.2),2),
              lambda:sh.compute_qgk(s.loading,np.full(2,.3),3),
              lambda:sh.sample_phi(-q,s.alpha,s.tau,3,4,2),
              lambda:sh.sample_phi(q,s.alpha,s.tau,3,4,2,1.6,1.5),
              lambda:sh.sample_delta_tau(q,s.alpha,s.phi,np.zeros(2),2,3,4),
              lambda:cg.sample_Lambda_twostage(self.data['Y'],s.eta,-s.sigma2,
                  np.ones((4,12)),s.alpha,s.phi,s.tau,np.full(2,.2),self.slices),
              lambda:cg.sample_Lambda_twostage(self.data['Y'],s.eta,s.sigma2,
                  np.full((4,12),2.),s.alpha,s.phi,s.tau,np.full(2,.2),self.slices),
              lambda:cg.sample_sigma2_twostage(self.data['Y'],np.zeros((4,12)),
                  np.ones((4,12)),2.,np.ones(4)),
              lambda:cg.compute_Yhat(s.loading.astype('float32'),s.eta,self.slices)]
        before=rng_hash(np.random.get_state())
        for call in bads:
            with self.assertRaises(ValueError):call()
            self.assertEqual(rng_hash(np.random.get_state()),before)

    def test_px_invalid_input_does_not_consume_generator(self):
        s=self.state;rng=np.random.default_rng(12);before=copy.deepcopy(rng.bit_generator.state)
        for alpha in [np.zeros(2),np.ones(3),np.array([1.,np.nan])]:
            with self.assertRaises(ValueError):px.refresh_alpha_gauge(s.loading,s.eta,alpha,rng,np.full(2,.2),'bad')
            self.assertEqual(before,rng.bit_generator.state)
        with self.assertRaises(ValueError):px.refresh_alpha_gauge(s.loading,s.eta,s.alpha,np.random.RandomState(1),np.full(2,.2),'bad')


if __name__ == '__main__':
    unittest.main()
