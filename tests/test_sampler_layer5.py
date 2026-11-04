"""Exact regression and independent split chronology/identity checks."""
import ast
import copy
import csv
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import blackjax
import jax
import jax.numpy as jnp
import numpy as np
from threadpoolctl import threadpool_limits

from bsfm.sampler import split_kernels as sk
from bsfm.sampler.contracts import logical_hash
from bsfm.sampler.layer4 import state_hashes
from bsfm.sampler.layer5 import SplitTransition
from sampler_layer5_support import (ROOT, canonical_system, gaussian_system,
                                    evaluate, tree_record)
from sampler_provenance import body_ast_sha256


class Layer5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.limit=threadpool_limits(limits=1); cls.limit.__enter__()
        cls.target,cls.state,cls.pos,cls.layer=canonical_system()
        cls.ids=cls.target.factor_ids
        cls.tuning=cls.layer.tuning(cls.pos.factor_id)
        cls.fixture=json.loads((ROOT/'tests/fixtures/sampler_layer5.json').read_text())
        cls.kw=dict(state_factor_ids=cls.ids)
        cls.key=jax.random.PRNGKey(182)
        cls.result=cls.layer.transition(cls.key,cls.pos,cls.state,cls.tuning,**cls.kw)

    @classmethod
    def tearDownClass(cls): cls.limit.__exit__(None,None,None)

    def test_exact_historical_saved_fixture(self):
        self.assertEqual(evaluate(),self.fixture['expected'])

    def test_public_canonical_endpoint_matches_reference_exactly(self):
        self.assertEqual(tree_record((self.result.nuts_state,self.result.info)),
                         self.fixture['expected']['canonical_transition'])

    def test_source_bodies_provenance(self):
        with (ROOT/'docs/sampler/LAYER5_SOURCE_MAP.csv').open(newline='') as f:
            rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),2)
        for r in rows:
            b=(ROOT/r['port_path']).read_bytes()
            self.assertEqual(hashlib.sha256(b).hexdigest(),r['port_file_sha256'])
            n=next(n for n in ast.parse(b).body if isinstance(n,ast.FunctionDef) and n.name==r['port_function'])
            self.assertEqual(body_ast_sha256(n),r['port_body_ast_sha256'])
            if r['port_function']=='build_split':
                self.assertEqual(r['body_ast_exact'],'False')
                original=copy.deepcopy(n)
                one=next(x for x in original.body if isinstance(x,ast.FunctionDef) and x.name=='one')
                expected=ast.parse("if jax.default_backend()=='gpu':\n    ac=gpu_acceptance_roundoff(ac)").body[0]
                guards=[x for x in one.body if ast.dump(x,include_attributes=False)==ast.dump(expected,include_attributes=False)]
                self.assertEqual(len(guards),1)
                guard=guards[0];index=one.body.index(guard)
                self.assertIsInstance(one.body[index-1],ast.Assign)
                self.assertEqual(ast.unparse(one.body[index-1].targets[0]),'ac')
                one.body.remove(guard)
                self.assertEqual(body_ast_sha256(original),r['source_body_ast_sha256'])
            else:
                self.assertEqual(r['body_ast_exact'],'True')
                self.assertEqual(body_ast_sha256(n),r['source_body_ast_sha256'])
            self.assertEqual([n.lineno,n.end_lineno],[int(r['port_start']),int(r['port_end'])])

    def test_analytic_gradient_bridge_matches_layer3(self):
        args,_=self.layer._inputs(self.key,self.pos,self.state,self.ids)
        ld=sk.make_logdensity(self.target._kernels)
        value,grad=self.target._kernels['value_grad'](*args)
        self.assertEqual(float(ld(*args)),float(value))
        np.testing.assert_array_equal(jax.grad(ld)(*args),grad)
        for arg in (1,2,3): np.testing.assert_array_equal(jax.grad(ld,argnums=arg)(*args),np.zeros_like(args[arg]))

    def test_partition_keys_fixed_w_no_hyper_likelihood_and_diagnostics(self):
        calls=[]; evaluations=[0]
        _,args,maps,ld=gaussian_system()
        def counted(q,u,ct,penalty):
            evaluations[0]+=1
            return ld(q,u,ct,penalty)
        original_init=blackjax.nuts.init
        field=np.array([0,1,4,5,6,7]); hyper=np.array([2,3])
        def fake_kernel(key,state,density,step,mass,**kw):
            index=len(calls); before=evaluations[0]
            value=density(state.position)
            if index==1: self.assertEqual(before,evaluations[0])
            shift=jnp.array(.02 if index==0 else -.03)
            nxt=original_init(state.position+shift,density)
            calls.append(dict(key=np.asarray(key),start=np.asarray(state.position),
                              step=float(step),mass=np.asarray(mass),depth=kw['max_num_doublings']))
            from types import SimpleNamespace
            return nxt,SimpleNamespace(acceptance_rate=jnp.array(.7+.1*index),
                 is_divergent=jnp.array(index==1),num_integration_steps=jnp.array(3+index),
                 energy=jnp.array(10.+index),momentum=jnp.arange(len(state.position),dtype=jnp.float64))
        with patch.object(blackjax.nuts,'build_kernel',return_value=fake_kernel),jax.disable_jit():
            core=sk.build_split(counted,maps,8)
            tuned=dict(step_size=.02,hyper_step_size=.03,inverse_mass_matrix=jnp.arange(1.,9.))
            final,info=core['transition'](jax.random.PRNGKey(3),*args,tuned)
        self.assertEqual(len(calls),2)
        for i,idx in enumerate((field,hyper)):
            np.testing.assert_array_equal(calls[i]['key'],jax.random.split(jax.random.PRNGKey(3))[i])
            np.testing.assert_array_equal(calls[i]['start'],np.asarray(args[0])[idx])
            np.testing.assert_array_equal(calls[i]['mass'],np.arange(1.,9.)[idx])
            self.assertEqual(calls[i]['depth'],10)
        pf=args[0].at[field].add(.02)
        old=maps['physical'](pf[2:4],pf[4:].reshape(-1,2))
        new=maps['physical'](final.position[2:4],final.position[4:].reshape(-1,2))
        np.testing.assert_allclose(new,old,atol=1e-15,rtol=1e-15)
        np.testing.assert_array_equal(final.position[:2],pf[:2])
        self.assertEqual(float(info.energy),10.)
        np.testing.assert_array_equal(info.momentum[hyper],np.zeros(2))
        self.assertTrue(bool(info.is_divergent));self.assertEqual(int(info.num_integration_steps),7)
        np.testing.assert_array_equal(info.block_energy,[10.,11.])

    def test_canonical_physical_w_preservation_independent_two_blocks(self):
        args,_=self.layer._inputs(self.key,self.pos,self.state,self.ids)
        p,u,ct,penalty=args; field=np.r_[0:2,4:len(p)]
        ld=sk.make_logdensity(self.target._kernels)
        density=lambda v:ld(p.at[field].set(v),u,ct,penalty)
        kernel=blackjax.nuts.build_kernel()
        # Match compiled evaluation of each block; no whole split helper used.
        def one(key):
            s=blackjax.nuts.init(p[field],density)
            return kernel(key,s,density,.01,jnp.ones(len(field)),max_num_doublings=10)
        fs,_=jax.jit(one)(jax.random.split(self.key)[0])
        pf=p.at[field].set(fs.position)
        maps=self.layer.centered._kernels
        w=maps['physical'](pf[2:4],pf[4:].reshape(-1,2))
        pn=jnp.asarray(self.result.position.values)
        wn=maps['physical'](pn[2:4],pn[4:].reshape(-1,2))
        self.assertLess(float(np.linalg.norm(wn-w)/max(np.linalg.norm(w),1e-100)),2e-8)

    def test_no_state_eta_or_response_mutation_and_no_draw(self):
        before=state_hashes(self.state); y=logical_hash(self.target.inputs.arrays['Y'])
        with patch.object(self.target,'draw_eta',side_effect=AssertionError('eta draw')):
            result=self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
        self.assertEqual(before,state_hashes(self.state))
        self.assertEqual(y,logical_hash(self.target.inputs.arrays['Y']))
        self.assertFalse(result.audit['eta_redrawn'])

    def test_same_process_exact(self):
        result=self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
        self.assertEqual(tree_record((result.nuts_state,result.info)),
                         tree_record((self.result.nuts_state,self.result.info)))

    def test_fresh_process_exact(self):
        script="from sampler_layer5_support import evaluate; import json,sys; from pathlib import Path; Path(sys.argv[1]).write_text(json.dumps(evaluate()))"
        env=dict(os.environ);env['PYTHONPATH']=os.pathsep.join([str(ROOT/'src'),str(ROOT/'tests')])
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out.json'
            subprocess.run([sys.executable,'-B','-c',script,str(out)],env=env,check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            self.assertEqual(json.loads(out.read_text()),self.fixture['expected'])

    def test_context_rebuilt_from_changed_state(self):
        other=copy.deepcopy(self.state);other.eta+=.1
        seen=[]
        def spy(key,p,u,ct,penalty,tuned):
            seen.append(np.asarray(ct))
            return self.result.nuts_state,self.result.info
        with patch.dict(self.layer._runner,transition=spy):
            a=self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
            b=self.layer.transition(self.key,self.pos,other,self.tuning,**self.kw)
        self.assertNotEqual(a.audit['context'],b.audit['context'])
        self.assertFalse(np.array_equal(*seen))

    def test_stale_position_and_factor_state_rejected_before_kernel(self):
        with patch.dict(self.layer._runner,transition=lambda *x: self.fail('kernel called')):
            for pos,ids in [(replace(self.pos,target_identity='bad'),self.ids),
                            (replace(self.pos,factor_id='bad'),self.ids),
                            (self.pos,tuple(reversed(self.ids)))]:
                with self.assertRaises(ValueError):
                    self.layer.transition(self.key,pos,self.state,self.tuning,state_factor_ids=ids)
            s=copy.deepcopy(self.state);s.alpha[0]*=2
            with self.assertRaises(ValueError):self.layer.transition(self.key,self.pos,s,self.tuning,**self.kw)

    def test_geometry_rule_input_mutation_rejected(self):
        for name,array_name in [('inputs','Y'),('geometry','locations'),('rule','omega')]:
            target,state,pos,layer=canonical_system()
            obj=getattr(target,name); original=obj.arrays[array_name]
            changed=np.array(original);changed.flat[0]+=.01
            setattr(target,name,replace(obj,arrays={**obj.arrays,array_name:changed}))
            with self.assertRaises(ValueError):
                layer.transition(self.key,pos,state,layer.tuning(pos.factor_id),state_factor_ids=target.factor_ids)

    def test_tuning_validation(self):
        for step in (0.,-1.,np.nan,np.inf,True,[.1]):
            with self.assertRaises(ValueError):self.layer.tuning(self.pos.factor_id,step_size=step)
            with self.assertRaises(ValueError):self.layer.tuning(self.pos.factor_id,hyper_step_size=step)
        for mass in (np.eye(self.layer.dimension),np.ones(2),np.zeros(self.layer.dimension),np.full(self.layer.dimension,np.inf)):
            with self.assertRaises(ValueError):self.layer.tuning(self.pos.factor_id,inverse_mass_matrix=mass)
        for tuned in (replace(self.tuning,factor_id=self.ids[1]),replace(self.tuning,target_identity='bad'),
                      replace(self.tuning,mass_sha256='bad')):
            with self.assertRaises(ValueError):self.layer.transition(self.key,self.pos,self.state,tuned,**self.kw)

    def test_tuning_and_endpoint_arrays_readonly(self):
        with self.assertRaises(ValueError):self.tuning.inverse_mass_matrix[0]=9
        with self.assertRaises(ValueError):self.result.position.values[0]=9

    def test_key_validation(self):
        for key in (12,np.array([1.,2.]),jax.random.split(self.key,2),jax.random.key(0,impl='rbg')):
            with self.assertRaises(ValueError):self.layer.transition(key,self.pos,self.state,self.tuning,**self.kw)
        self.assertEqual(self.layer._key(jax.random.key(182)),self.layer._key(self.key))

    def test_adaptation_minimum_and_integer(self):
        for steps in (0,19,20.,True):
            with self.assertRaises(ValueError):self.layer.adapt(self.key,self.pos,self.state,steps=steps,**self.kw)

    def test_warmup_independent_tuning_and_endpoint(self):
        core,args,_,_=gaussian_system()
        (state,tuned),hist=core['adapt'](jax.random.PRNGKey(173),*args,100)
        np.testing.assert_array_equal(state.position,np.asarray(hist.state.position)[-1])
        self.assertFalse(np.array_equal(state.position,args[0]))
        self.assertNotEqual(float(tuned['step_size']),float(tuned['hyper_step_size']))
        self.assertFalse(np.array_equal(tuned['inverse_mass_matrix'],np.ones(8)))
        self.assertEqual(tree_record(((state,tuned),hist)),self.fixture['expected']['gaussian_adapt'])

    def test_public_adaptation_propagates_endpoint_and_freezes_tuning(self):
        # Exercise the public adapter with an already checked endpoint; real
        # numerical window adaptation is independently tested above.
        ns=self.result.nuts_state; info=self.result.info
        hist=sk.History(jax.tree.map(lambda x:jnp.stack([x]*20),ns),
                        jax.tree.map(lambda x:jnp.stack([x]*20),info),None)
        tuning=dict(step_size=jnp.array(.03),hyper_step_size=jnp.array(.04),inverse_mass_matrix=jnp.ones(self.layer.dimension)*2)
        with patch.dict(self.layer._runner,adapt=lambda *x:((ns,tuning),hist)):
            result=self.layer.adapt(self.key,self.pos,self.state,steps=20,**self.kw)
        np.testing.assert_array_equal(result.endpoint.position.values,ns.position)
        self.assertEqual(result.tuning.step_size,.03);self.assertEqual(result.tuning.hyper_step_size,.04)
        self.assertFalse(result.tuning.inverse_mass_matrix.flags.writeable)
        self.assertEqual(state_hashes(self.state),result.endpoint.audit['state_array_hashes'])

    def test_invariant_failure_fatal_and_divergence_visible(self):
        bad=self.result.info._replace(hyper_W_relative_error=jnp.array(2e-8))
        with patch.dict(self.layer._runner,transition=lambda *x:(self.result.nuts_state,bad)):
            with self.assertRaises(RuntimeError):self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
        info=self.result.info._replace(block_divergent=jnp.array([True,False]),is_divergent=jnp.array(True))
        with patch.dict(self.layer._runner,transition=lambda *x:(self.result.nuts_state,info)):
            result=self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
        self.assertTrue(result.info.is_divergent)

    def test_nonfinite_endpoint_and_nondivergent_energy_rejected(self):
        bad=self.result.nuts_state._replace(logdensity=jnp.array(np.nan))
        with patch.dict(self.layer._runner,transition=lambda *x:(bad,self.result.info)):
            with self.assertRaises(RuntimeError):self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)
        bad=self.result.info._replace(block_energy=jnp.array([np.inf,1.]),block_divergent=jnp.array([False,False]))
        with patch.dict(self.layer._runner,transition=lambda *x:(self.result.nuts_state,bad)):
            with self.assertRaises(RuntimeError):self.layer.transition(self.key,self.pos,self.state,self.tuning,**self.kw)


if __name__=='__main__':unittest.main()
