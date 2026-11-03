"""One-sweep chronology, independent literal fixture, boundary and failure tests."""
from contextlib import ExitStack
import copy
import ast
import csv
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import jax
import jax.numpy as jnp
import numpy as np
from threadpoolctl import threadpool_limits

from bsfm.sampler import layer6 as l6
from bsfm.sampler import field_target
from bsfm.sampler.field_target import FieldPosition
from bsfm.sampler import layer4 as l4
from bsfm.sampler.layer4 import state_hashes, JointEtaConditional
from bsfm.sampler.layer5 import SplitResult, SplitTransition, PreparedContext
from bsfm.sampler.joint_eta_kernels import JointEtaDiagnostics
from sampler_layer6_support import (ROOT, fixture_system, independent_rng, run_case,
                                    record_result)

FIXTURE=json.loads((ROOT/'tests/fixtures/sampler_layer6.json').read_text())


class Layer6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads=threadpool_limits(limits=1);cls.threads.__enter__()
        cls.target,cls.initial,cls.positions,cls.layer,cls.tuning,cls.scale=fixture_system()
        saved=np.random.get_state()
        try:
            np.random.seed(491);rng=np.random.default_rng(193);gauge=np.random.default_rng(307)
            cls.real=cls.layer.sweep(cls.initial,cls.positions,cls.tuning,eta_rng=rng,gauge_rng=gauge,
                master_key=jax.random.PRNGKey(419),state_factor_ids=cls.target.factor_ids,label='sweep_0001')
            cls.actual_rng=independent_rng(rng,gauge,cls.real.master_key)
            cls.after_first_global=np.random.get_state()
            cls.after_first_eta=copy.deepcopy(rng);cls.after_first_gauge=copy.deepcopy(gauge)
        finally:np.random.set_state(saved)

    @classmethod
    def tearDownClass(cls):cls.threads.__exit__(None,None,None)

    def setUp(self):self.saved_global=np.random.get_state()
    def tearDown(self):np.random.set_state(self.saved_global)

    def kwargs(self):
        return dict(eta_rng=np.random.default_rng(193),gauge_rng=np.random.default_rng(307),
                    master_key=jax.random.PRNGKey(419),state_factor_ids=self.target.factor_ids,label='sweep_0001')

    def test_exact_literal_fixture_all_state_diagnostics_and_streams(self):
        self.assertEqual(record_result(self.real),FIXTURE['expected'])
        self.assertEqual(self.actual_rng,self.real.audit['rng_after'])

    def test_coherent_yhat_domains_positions_and_order(self):
        r=self.real;slices=r.state.validate(self.target.inputs,factors=2)
        np.testing.assert_array_equal(l6.compute_Yhat(r.state.loading,r.state.eta,slices),r.fitted_Y)
        self.assertEqual(len(r.pcg_diagnostics),3)
        self.assertEqual(sorted(r.factor_order),[0,1])
        self.assertEqual([p.factor_id for p in r.positions],list(self.target.factor_ids))
        for i,p in enumerate(r.positions):l6.validate_chart_state(self.target,p,r.state,i)

    def test_exact_px_invariants_and_no_mutation(self):
        self.assertEqual(state_hashes(self.initial),self.real.audit['state_before'])
        self.assertEqual([l6.contracts.logical_hash(p.values) for p in self.positions],self.real.audit['positions_before'])
        self.assertLessEqual(max(self.real.px_audit['checks_relative'].values()),5e-13)
        self.assertTrue(self.real.px_audit['identified_state_preserved'])
        for n in l6.STATE_ARRAYS:self.assertFalse(np.shares_memory(getattr(self.initial,n),getattr(self.real.state,n)))
        for a,b in zip(self.positions,self.real.positions):self.assertFalse(np.shares_memory(a.values,b.values))

    def test_derived_hypers_preserve_order_and_fixed_rule(self):
        for p,row in zip(self.real.positions,self.real.warp_summaries):
            self.assertEqual(row['factor_id'],p.factor_id);self.assertEqual(row['ell_eta'],.14)
            self.assertEqual(row['ell_W'],float(np.exp(p.values[2])))
            expected=float(np.exp(np.asarray(jnp.asarray(p.values[3])+(jnp.asarray(p.values[2])-.5*np.log(10.)))))
            self.assertEqual(row['sigma_W'],expected)

    def instrumented(self):
        """Real conjugates/PX, instrumented cheap PCG/NUTS/single-eta endpoints.

        The separate real fixture covers numerical outputs. This instrument
        checks ordering without copying the orchestration's control flow.
        """
        target,state,ps,layer,tuning,scale=fixture_system();events=[];contexts=[];keys=[]
        eta_rng=np.random.default_rng(193);gauge=np.random.default_rng(307)
        args=dict(eta_rng=eta_rng,gauge_rng=gauge,master_key=jax.random.PRNGKey(419),state_factor_ids=target.factor_ids,label='sweep_0001')
        current=[None];new_etas={};order_record=[]
        def wrapper(fn,event):
            def call(*a,**kw):
                events.append(event)
                if event=='sigma2':
                    self.assertIs(a[4],layer._b_sigma2)
                    self.assertEqual(a[3],2.0)
                    np.testing.assert_array_equal(a[4],scale)
                result=fn(*a,**kw)
                if event=='PX':
                    old_l,old_e,old_a=a[:3];new_l,new_e,new_a=result[:3]
                    pairs=[(old_l*old_a[None,None,:],new_l*new_a[None,None,:]),
                           (old_e/old_a[:,None],new_e/new_a[:,None])]
                    # Independently rebuild the actual type-block fitted Y.
                    def fit(l,e):return np.column_stack([l[c]@e[:,i] for i,c in enumerate(target.inputs.arrays['cell_id'])])
                    pairs.append((fit(old_l,old_e),fit(new_l,new_e)))
                    def quadratic(l,alpha):
                        q=(np.sum(l*l,axis=0)-.2*np.sum(l,axis=0)**2/(.8+l.shape[0]*.2))/.8
                        return q*alpha[None,:]**2
                    pairs.append((quadratic(old_l,old_a),quadratic(new_l,new_a)))
                    for before,after in pairs:
                        self.assertLessEqual(np.max(np.abs(after-before))/max(1.,np.max(np.abs(before))),5e-13)
                return result
            return call
        context_fn=target.context
        def context(s,**kw):
            i=target.factor_ids.index(kw['factor_id']);events.append(f'context:{i}')
            contexts.append((i,s.eta.copy()))
            return context_fn(s,**kw)
        def features(p):
            i=target.factor_ids.index(p.factor_id);events.append(f'feature:{i}')
            return np.zeros((3,2)),np.zeros((3,2)),np.ones((3,1024))
        def joint(rng,**kw):
            events.append('joint_eta');self.assertIs(rng,eta_rng)
            self.assertEqual(kw['maximum_iterations'],80);self.assertEqual(kw['tolerance'],1e-10)
            eta=rng.normal(0,.1,(2,3))
            return eta,np.zeros((2,1024)),JointEtaDiagnostics(1,0.,0.,0.,1e-10,True,0.,0.,1.)
        def transition(key,p,s,t,*,state_factor_ids,prepared_context):
            i=target.factor_ids.index(p.factor_id);events.append(f'transition:{i}');current[0]=i
            keys.append(np.asarray(key).copy());self.assertIs(t,tuning[i])
            values=p.values.copy();values[0]+=.03;values[1]-=.02
            out=FieldPosition(values,p.factor_id,p.target_identity)
            info=SimpleNamespace(is_divergent=True,hyper_W_relative_error=0.)
            return SplitResult(out,None,info,dict(context=json.loads(prepared_context.context_json)))
        def single(rng,**kw):
            i=current[0];events.append(f'eta:{i}');self.assertIs(rng,eta_rng)
            draw=rng.normal(0,.1,3)+i;new_etas[i]=draw.copy();return draw
        original_permutation=np.random.permutation
        def permutation(k):
            events.append('permutation');independent=np.random.RandomState();independent.set_state(np.random.get_state())
            expected=independent.permutation(k);actual=original_permutation(k)
            np.testing.assert_array_equal(actual,expected);order_record.extend(actual.tolist());return actual
        original_split=jax.random.split
        def split(key,*a,**kw):events.append('master_key_split');return original_split(key,*a,**kw)
        np.random.seed(491)
        with ExitStack() as stack:
            for name,event in [('sample_Lambda_twostage','Lambda'),('compute_Yhat','Yhat'),('sample_sigma2_twostage','sigma2'),('compute_qgk','qgk'),('sample_phi','phi'),('sample_delta_tau','delta_tau'),('refresh_alpha_gauge','PX')]:
                stack.enter_context(patch.object(l6,name,side_effect=wrapper(getattr(l6,name),event)))
            stack.enter_context(patch.object(target,'context',side_effect=context))
            stack.enter_context(patch.object(target,'features',side_effect=features))
            stack.enter_context(patch.object(l4,'sample_joint_eta_pcg',side_effect=joint))
            stack.enter_context(patch.object(layer.split,'transition',side_effect=transition))
            stack.enter_context(patch.object(field_target,'sample_single_eta',side_effect=single))
            stack.enter_context(patch.object(np.random,'permutation',side_effect=permutation))
            stack.enter_context(patch.object(jax.random,'split',side_effect=split))
            result=layer.sweep(state,ps,tuning,**args)
        return result,events,contexts,keys,new_etas,order_record

    def test_instrumented_exact_call_order_counts_and_no_extra_eta(self):
        r,events,contexts,keys,etas,order=self.instrumented()
        expected=['Lambda','feature:0','feature:1','joint_eta','Yhat','sigma2']*3
        expected+=['qgk','phi','delta_tau','PX','Yhat','permutation']
        for i in order:expected += [f'context:{i}','master_key_split',f'transition:{i}',f'context:{i}',f'feature:{i}',f'eta:{i}','Yhat']
        self.assertEqual(events,expected)
        self.assertEqual(len(r.pcg_diagnostics),3)
        self.assertEqual(len(r.factor_diagnostics),2)
        self.assertEqual(tuple(order),r.factor_order)
        self.assertTrue(all(x['transition'].info.is_divergent for x in r.factor_diagnostics))
        master=jax.random.PRNGKey(419)
        for actual in keys:
            master,step=jax.random.split(master);np.testing.assert_array_equal(actual,step)
        np.testing.assert_array_equal(master,r.master_key)
        first,second=order
        np.testing.assert_array_equal(contexts[2][1][first],etas[first])
        np.testing.assert_array_equal(contexts[3][1],contexts[2][1])
        for i in order:np.testing.assert_array_equal(r.state.eta[i],etas[i])

    def test_rejected_inputs_do_not_consume_streams(self):
        cases=[('positions',tuple(reversed(self.positions))),('tuning',tuple(reversed(self.tuning))),('positions',self.positions[:1]),('tuning',self.tuning[:1])]
        for name,value in cases:
            kw=self.kwargs();before=independent_rng(kw['eta_rng'],kw['gauge_rng'],kw['master_key'])
            with self.assertRaises(ValueError):
                self.layer.sweep(self.initial,value if name=='positions' else self.positions,
                                 value if name=='tuning' else self.tuning,**kw)
            self.assertEqual(before,independent_rng(kw['eta_rng'],kw['gauge_rng'],kw['master_key']))

    def test_foreign_state_factor_ids_position_tuning_and_scale(self):
        for edit in ('state','factor_ids','position','tuning','scale'):
            target,state,ps,layer,tuning,scale=fixture_system();kw=self.kwargs()
            if edit=='state':state.input_identity_json='bad'
            if edit=='factor_ids':kw['state_factor_ids']=tuple(reversed(target.factor_ids))
            if edit=='position':ps=(replace(ps[0],target_identity='bad'),ps[1])
            if edit=='tuning':tuning=(replace(tuning[0],mass_sha256='bad'),tuning[1])
            if edit=='scale':layer._b_sigma2=scale*2
            with self.assertRaises(ValueError):layer.sweep(state,ps,tuning,**kw)

    def test_input_mesh_rule_and_target_replacement_rejected(self):
        for name,axis in [('inputs','Y'),('geometry','locations'),('rule','omega')]:
            target,state,ps,layer,tuning,_=fixture_system()
            obj=getattr(target,name);values=np.array(obj.arrays[axis],copy=True);values.flat[0]+=.01
            setattr(target,name,replace(obj,arrays={**obj.arrays,axis:values}))
            with self.assertRaises(ValueError):layer.sweep(state,ps,tuning,**self.kwargs())
        _,state,ps,layer,tuning,_=fixture_system();layer.target=self.target
        with self.assertRaises(ValueError):layer.sweep(state,ps,tuning,**self.kwargs())

    def test_bad_rng_alias_key_label_and_prior(self):
        for edit in ('generator','alias','shared_bit_generator','key','label'):
            kw=self.kwargs()
            if edit=='generator':kw['eta_rng']=np.random.RandomState(1)
            if edit=='alias':kw['gauge_rng']=kw['eta_rng']
            if edit=='shared_bit_generator':kw['gauge_rng']=np.random.Generator(kw['eta_rng'].bit_generator)
            if edit=='key':kw['master_key']=42
            if edit=='label':kw['label']=''
            with self.assertRaises(ValueError):self.layer.sweep(self.initial,self.positions,self.tuning,**kw)
        with self.assertRaises(ValueError):l6.GibbsSweep(self.target,b_sigma2=self.scale*2)

    def test_pcg_failure_no_partial_result_and_rng_not_rolled_back(self):
        kw=self.kwargs();np.random.seed(491)
        before=independent_rng(kw['eta_rng'],kw['gauge_rng'],kw['master_key']);state_before=state_hashes(self.initial)
        with patch.object(self.layer,'_joint_eta',side_effect=RuntimeError('PCG failed')) as fail:
            with self.assertRaisesRegex(RuntimeError,'PCG failed'):self.layer.sweep(self.initial,self.positions,self.tuning,**kw)
        self.assertEqual(fail.call_count,1)
        self.assertEqual(state_before,state_hashes(self.initial))
        self.assertNotEqual(before['numpy_global_sha256'],independent_rng(kw['eta_rng'],kw['gauge_rng'],kw['master_key'])['numpy_global_sha256'])

    def test_physical_w_failure_not_retried_or_returned(self):
        kw=self.kwargs();before=state_hashes(self.initial)
        fake=JointEtaDiagnostics(1,0.,0.,0.,1e-10,True,0.,0.,1.)
        with patch.object(self.layer,'_joint_eta',return_value=(self.initial.eta.copy(),fake)),patch.object(self.layer.split,'transition',side_effect=RuntimeError('physical W failed')) as fail:
            with self.assertRaisesRegex(RuntimeError,'physical W failed'):self.layer.sweep(self.initial,self.positions,self.tuning,**kw)
        self.assertEqual(fail.call_count,1);self.assertEqual(before,state_hashes(self.initial))

    def test_pcg_false_convergence_and_nonfinite_draw_rejected(self):
        fake=JointEtaDiagnostics(80,1.,1.,1.,1e-10,False,0.,0.,1.)
        for eta,diag in [(self.initial.eta.copy(),fake),(np.full_like(self.initial.eta,np.nan),replace(fake,converged=True))]:
            with patch.object(l4,'sample_joint_eta_pcg',return_value=(eta,np.zeros((2,1024)),diag)):
                with self.assertRaises((RuntimeError,ValueError)):
                    self.layer._joint_eta(self.positions,self.initial,np.random.default_rng(0))

    def test_exact_forward_chart_acceptance_without_changing_endpoint(self):
        # A real accepted Layer-5 fixture is not exactly invertible at the bit level.
        old=json.loads((ROOT/'tests/fixtures/sampler_layer5.json').read_text())['expected']['canonical_position']
        p=replace(self.positions[0],values=np.array(old));s=copy.deepcopy(self.initial)
        s.alpha[0]=float(np.exp(p.values[0]));s.zeta[0]=float(jax.nn.sigmoid(jnp.asarray(p.values[1])))
        self.assertNotEqual(p.values[0],np.log(s.alpha[0]))
        from scipy.special import logit
        self.assertNotEqual(p.values[1],logit(s.zeta[0]))
        before=p.values.copy();l6.validate_chart_state(self.target,p,s,0);np.testing.assert_array_equal(p.values,before)
        s.alpha[0]*=1.000001
        with self.assertRaises(ValueError):l6.validate_chart_state(self.target,p,s,0)

    def test_completed_endpoint_is_valid_next_sweep_input(self):
        kw=self.kwargs();r=self.real
        self.layer._validate(r.state,r.positions,self.tuning,kw['eta_rng'],kw['gauge_rng'],r.master_key,
                             self.target.factor_ids,'next-sweep-boundary-only')

    def prepared(self):
        return self.layer.split.prepare_context(self.positions[0],self.initial,
                                               state_factor_ids=self.target.factor_ids)

    def consume(self,ctx,state=None,position=None,split=None):
        return (split or self.layer.split).transition(jax.random.PRNGKey(1),
            position or self.positions[0],state or self.initial,self.tuning[0],
            state_factor_ids=self.target.factor_ids,prepared_context=ctx)

    def test_prepared_context_rejects_every_state_array_change(self):
        ctx=self.prepared()
        for name in l6.STATE_ARRAYS:
            changed=copy.deepcopy(self.initial)
            getattr(changed,name).flat[0]*=1.001
            with self.subTest(name=name),self.assertRaises(ValueError):self.consume(ctx,changed)

    def test_prepared_context_immutable_and_unissued_foreign_rejected(self):
        ctx=self.prepared()
        for a in (ctx.u,ctx.ct):
            with self.assertRaises(ValueError):a.flags.writeable=True
        # Even an otherwise identical record was not issued by this boundary.
        with self.assertRaisesRegex(ValueError,'Unissued'):self.consume(replace(ctx))
        other=SplitTransition(self.target)
        with self.assertRaisesRegex(ValueError,'foreign'):self.consume(ctx,split=other)
        with self.assertRaisesRegex(ValueError,'Unissued'):self.consume((ctx.u,ctx.ct,ctx.penalty))

    def test_prepared_context_corrupted_payload_or_identity_rejected(self):
        for name,value in [('u',np.ones(3)),('ct',np.ones(3)),('penalty',.123),
                           ('context_json','{}'),('position_sha256','bad')]:
            ctx=self.prepared()
            # Deliberate frozen-record bypass simulates corrupted in-memory data.
            object.__setattr__(ctx,name,value)
            with self.subTest(name=name),self.assertRaisesRegex(ValueError,'changed'):self.consume(ctx)

    def test_prepared_context_changed_position_rejected(self):
        ctx=self.prepared();values=self.positions[0].values.copy();values[4]+=.001
        with self.assertRaisesRegex(ValueError,'Stale'):
            self.consume(ctx,position=replace(self.positions[0],values=values))
        with self.assertRaises(ValueError):self.consume(ctx,position=self.positions[1])

    def test_public_layers_accept_real_forward_rounded_layer5_endpoint(self):
        values=json.loads((ROOT/'tests/fixtures/sampler_layer5.json').read_text())['expected']['canonical_position']
        p=replace(self.positions[0],values=np.array(values));state=copy.deepcopy(self.initial)
        state.alpha[0]=float(np.exp(p.values[0]))
        state.zeta[0]=float(jax.nn.sigmoid(jnp.asarray(p.values[1])))
        before=state_hashes(state);positions=(p,self.positions[1])
        eta,_,diag,_=self.layer.joint_eta.draw(positions,state,np.random.default_rng(71),
                                            state_factor_ids=self.target.factor_ids)
        self.assertTrue(diag.converged);self.assertTrue(np.isfinite(eta).all())
        ctx=self.layer.split.prepare_context(p,state,state_factor_ids=self.target.factor_ids)
        result=self.layer.split.transition(jax.random.PRNGKey(73),p,state,self.tuning[0],
            state_factor_ids=self.target.factor_ids,prepared_context=ctx)
        self.assertTrue(np.isfinite(result.position.values).all())
        self.assertEqual(before,state_hashes(state))
        self.public_endpoint_summary=dict(joint_eta_iterations=diag.iterations,
                                         transition_W_error=result.audit['maximum_W_relative_error'])

    def test_direct_and_prepared_public_transition_exact(self):
        ctx=self.prepared();prepared=self.consume(ctx)
        direct=self.layer.split.transition(jax.random.PRNGKey(1),self.positions[0],self.initial,
                                          self.tuning[0],state_factor_ids=self.target.factor_ids)
        from sampler_layer5_support import tree_record
        self.assertEqual(tree_record((prepared.nuts_state,prepared.info)),
                         tree_record((direct.nuts_state,direct.info)))
        self.assertEqual(prepared.audit,direct.audit)

    def test_shared_chart_initial_and_minimal_inconsistent_changes(self):
        for i,p in enumerate(self.positions):
            l6.validate_chart_state(self.target,p,self.initial,i)
        for name,direction in [('alpha',np.inf),('zeta',-np.inf)]:
            state=copy.deepcopy(self.initial);a=getattr(state,name)
            a[0]=np.nextafter(a[0],direction)
            with self.subTest(name=name),self.assertRaises(ValueError):
                l6.validate_chart_state(self.target,self.positions[0],state,0)
        # exp/sigmoid are not injective on float64 charts. The nearest chart
        # mismatch is just beyond the exact-forward rounding plateau: 3/2 ULPs.
        for coordinate,direction,steps in [(0,-np.inf,3),(1,np.inf,2)]:
            a=self.positions[0].values.copy()
            for _ in range(steps-1):
                a[coordinate]=np.nextafter(a[coordinate],direction)
                l6.validate_chart_state(self.target,replace(self.positions[0],values=a),self.initial,0)
            a[coordinate]=np.nextafter(a[coordinate],direction)
            with self.subTest(coordinate=coordinate),self.assertRaises(ValueError):
                l6.validate_chart_state(self.target,replace(self.positions[0],values=a),self.initial,0)

    def test_layer6_has_only_public_numerical_composition(self):
        source=(ROOT/'src/bsfm/sampler/layer6.py').read_text()
        tree=ast.parse(source)
        attrs={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertFalse({'_runner','_kernels','_result','_check','_tuning','_key'} & attrs)
        self.assertNotIn('sample_joint_eta_pcg',source)
        self.assertIn('self.joint_eta.draw(',source)
        self.assertIn('self.split.prepare_context(',source)
        self.assertIn('self.split.transition(',source)

    def test_two_consecutive_public_sweeps(self):
        # Continue the actual setUpClass first sweep with its exact live streams.
        first=self.real
        np.random.set_state(self.after_first_global)
        rng=copy.deepcopy(self.after_first_eta);gauge=copy.deepcopy(self.after_first_gauge)
        second=self.layer.sweep(first.state,first.positions,self.tuning,eta_rng=rng,gauge_rng=gauge,
            master_key=first.master_key,state_factor_ids=self.target.factor_ids,label='sweep_0002')
        self.assertEqual(second.audit['rng_before'],first.audit['rng_after'])
        self.assertEqual(second.audit['state_before'],first.audit['state_after'])
        self.assertEqual(second.audit['positions_before'],first.audit['positions_after'])
        self.assertEqual(len(second.pcg_diagnostics),3)
        slices=second.state.validate(self.target.inputs,factors=2)
        np.testing.assert_array_equal(second.fitted_Y,l6.compute_Yhat(second.state.loading,second.state.eta,slices))
        for i,p in enumerate(second.positions):l6.validate_chart_state(self.target,p,second.state,i)
        type(self).second_sweep_record=record_result(second)

    def test_fresh_process_exact(self):
        env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')])
        code="from sampler_layer6_support import run_case;import json,sys;from pathlib import Path;Path(sys.argv[1]).write_text(json.dumps(run_case()))"
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json'
            subprocess.run([sys.executable,'-B','-c',code,str(out)],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(json.loads(out.read_text()),FIXTURE['expected'])

    def test_same_process_exact(self):self.assertEqual(run_case(),FIXTURE['expected'])

    def test_source_and_chronology_map(self):
        with (ROOT/'docs/sampler/LAYER6_SOURCE_MAP.csv').open(newline='') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),13)
        for row in rows:
            self.assertEqual(row['source_sha256'],FIXTURE['source']['sha256'])
            self.assertEqual(int(row['source_bytes']),94890)
            b=(ROOT/row['port_path']).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),row['port_file_sha256'])
        self.assertEqual(FIXTURE['source']['inner_statement_lines'],[1123,1127,1128,1131,1143,1145,1146])
        self.assertEqual(FIXTURE['source']['factor_statement_lines'][-2:],[1263,1270])


if __name__=='__main__':unittest.main()
