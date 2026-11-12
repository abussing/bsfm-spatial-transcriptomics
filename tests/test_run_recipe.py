"""Real small transitions with explicitly mocked Git/environment/input attestation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from bsfm.sampler.run import run_recipe,validate_recipe,check_repository,main
from bsfm.sampler.run_storage import file_record
from test_meeting_extensions import setup


class RunRecipeTests(unittest.TestCase):
    def test_deep_and_flat_phases_and_completed_nonreplay(self):
        for mode in ('deep','flat','flat_learned_range'):
            model='flat' if mode=='flat_learned_range' else mode
            with self.subTest(model=mode),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); c=setup(root/'fixture','deep')
                payload=root/'input';payload.write_bytes(b'authenticated synthetic fixture')
                files={'fixture':dict(path='input',**file_record(payload))}
                recipe=dict(schema='bsfm.sampler-run.v1',backend='cpu',model=model,
                    chain_id='chain',factor_ids=list(c.target.factor_ids),seed=491,files=files,
                    dataset_recipe=None,gpu_runtime=None,phases=[
                        dict(run_id='bridge',warmup_steps=20,sweeps=1,save_every=2),
                        dict(run_id='production',warmup_steps=20,sweeps=2,save_every=2)])
                if mode=='flat_learned_range':
                    recipe['flat_range_prior']=dict(median=.18,log_sd=.25,initial=.14)
                path=root/'run.json';path.write_text(json.dumps(recipe))
                env=dict(lock=dict(sha256='a'*64),backend='cpu',test_only=True)
                with patch('bsfm.sampler.run.check_repository'), \
                     patch('bsfm.sampler.run_inputs.authenticate_environment',return_value=env), \
                     patch('bsfm.sampler.run_inputs.load_inputs',return_value=(
                         c.target,c.loading,c.eta,c.store.input_receipt)):
                    result=run_recipe(path,root/'outputs',commit='9'*40)
                    self.assertEqual(result['production_run_id'],'production')
                    self.assertEqual([p['result']['completed'] for p in result['phases']],[1,2])
                    self.assertEqual([p['result']['retained'] for p in result['phases']],[1,2])
                    with patch('bsfm.sampler.layer6.GibbsSweep.sweep',side_effect=AssertionError('Replay')), \
                         patch('bsfm.sampler.run_controller.RunController._adapt_endpoint',side_effect=AssertionError('Retune')), \
                         patch('bsfm.sampler.run_readaptation.ReadaptationController._adapt_endpoint',side_effect=AssertionError('Retune')):
                        self.assertEqual(run_recipe(path,root/'outputs',commit='9'*40),result)
                    child=json.loads((root/'outputs/production/input-receipt.json').read_text())
                    self.assertIn('readaptation_parent',child)
                    if model=='deep':
                        source=root/'outputs/bridge/segments/segment/genesis/endpoint.npz'
                        imported=copy.deepcopy(recipe)
                        imported['initial_endpoint']=dict(path=str(source),**file_record(source))
                        imported['pcg_maximum_iterations']=320
                        imported['phases']=imported['phases'][:1]
                        fork=root/'fork.json';fork.write_text(json.dumps(imported))
                        from dataclasses import replace
                        from bsfm.sampler.joint_eta_kernels import sample_joint_eta_pcg
                        def report_long_solve(*args,**kwargs):
                            a,b,diagnostics=sample_joint_eta_pcg(*args,**kwargs)
                            return a,b,replace(diagnostics,iterations=81)
                        with patch('bsfm.sampler.run_controller.RunController._adapt_endpoint',side_effect=AssertionError('Retune')), patch('bsfm.sampler.layer4.sample_joint_eta_pcg',side_effect=report_long_solve):
                            result2=run_recipe(fork,root/'fork',commit='8'*40)
                            self.assertEqual(result2['phases'][0]['result']['completed'],1)
                        import numpy as np
                        from bsfm.sampler.run_genesis import load_genesis
                        old=root/'outputs/bridge/segments/segment/boundaries/000000000001/record.npz'
                        new=root/'fork/bridge/segments/segment/boundaries/000000000001/record.npz'
                        with np.load(old) as a,np.load(new) as b:
                            for key in a.files:
                                if key!='metadata':np.testing.assert_array_equal(a[key],b[key])
                        source_bytes=source.read_bytes();source.write_bytes(source_bytes+b'changed')
                        with self.assertRaisesRegex(ValueError,'Input file changed'):
                            run_recipe(fork,root/'fork',commit='8'*40)
                        source.write_bytes(source_bytes)
                        # A published checkpoint may seed an inherited-tuning
                        # phase even though its original run had a longer plan.
                        parent=root/'outputs/production';segment=parent/'segments/segment'
                        paths=dict(spec=parent/'run-spec.json',inputs=parent/'input-receipt.json',
                            genesis=segment/'genesis/endpoint.npz',genesis_receipt=segment/'genesis/receipt.json',
                            boundary_receipt=segment/'boundaries/000000000001/receipt.json')
                        inherited=copy.deepcopy(recipe)
                        inherited['initial_checkpoint']={k:dict(path=str(p),**file_record(p)) for k,p in paths.items()}
                        inherited['phases']=[dict(run_id='settle',warmup_steps=0,sweeps=1,save_every=1)]
                        inherit_path=root/'inherit.json';inherit_path.write_text(json.dumps(inherited))
                        with patch('bsfm.sampler.run_controller.RunController._adapt_endpoint',side_effect=AssertionError('Retune')):
                            first=run_recipe(inherit_path,root/'inherit',commit='7'*40)
                            with patch('bsfm.sampler.layer6.GibbsSweep.sweep',side_effect=AssertionError('Replay')):
                                self.assertEqual(first,run_recipe(inherit_path,root/'inherit',commit='7'*40))
                        from bsfm.sampler.run_chart import geometry_from_genesis
                        restored=geometry_from_genesis(c.target.geometry.arrays,json.loads(c.target.geometry.identity_json),
                            root/'inherit/settle/segments/segment/genesis/endpoint.npz')
                        self.assertEqual(restored.spectral_identity,c.target.geometry.spectral_identity)
                    changed=copy.deepcopy(recipe);changed['phases'][1]['sweeps']=3
                    path.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):run_recipe(path,root/'outputs',commit='9'*40)

    def test_repository_and_recipe_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'file required'):
                check_repository(Path(tmp)/'untracked.json','0'*40)
        base=dict(schema='bsfm.sampler-run.v1',backend='cpu',model='deep',chain_id='chain',
            factor_ids=['one'],seed=1,files={},dataset_recipe=None,gpu_runtime=None,
            phases=[dict(run_id='production',warmup_steps=20,sweeps=2,save_every=1)])
        validate_recipe(base)
        for changes in [dict(backend='gpu'),dict(model='unknown'),dict(seed=True),
                        dict(factor_ids=['one','one']),dict(phases=[]),dict(chain_id='../escape')]:
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_recipe(dict(base,**changes))
        for changes in [dict(run_id='../escape'),dict(warmup_steps=0),dict(sweeps=True),dict(save_every=0)]:
            bad=copy.deepcopy(base);bad['phases'][0].update(changes)
            with self.assertRaises(ValueError):validate_recipe(bad)

    def test_external_recipe_still_requires_clean_exact_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            recipe=Path(tmp)/'run.json';recipe.write_text('{}')
            with patch('bsfm.sampler.run.subprocess.check_output',side_effect=['a'*40+'\n','']):
                check_repository(recipe,'a'*40)
            for responses in [('b'*40+'\n',),('a'*40+'\n',' M source.py')]:
                with patch('bsfm.sampler.run.subprocess.check_output',side_effect=responses):
                    with self.assertRaisesRegex(ValueError,'Clean exact'):
                        check_repository(recipe,'a'*40)

    def test_checkpoint_recipe_validation_does_not_import_jax(self):
        import subprocess,sys
        code="from bsfm.sampler.run import validate_checkpoint_source; import sys; validate_checkpoint_source({k:dict(path='x',bytes=1,sha256='a'*64) for k in ('spec','inputs','genesis','genesis_receipt','boundary_receipt')}); assert 'jax' not in sys.modules"
        subprocess.run([sys.executable,'-c',code],check=True)

    def test_cli_configures_explicit_gpu_before_execution(self):
        import os
        recipe=dict(schema='bsfm.sampler-run.v1',backend='gpu',model='deep',chain_id='chain',
            factor_ids=['one'],seed=1,files={},dataset_recipe=None,gpu_runtime={'blas_threads':1},
            phases=[dict(run_id='production',warmup_steps=20,sweeps=2,save_every=1)])
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'recipe.json';path.write_text(json.dumps(recipe))
            with patch.dict(os.environ,{},clear=False),patch('bsfm.sampler.run.run_recipe',return_value={}) as execute, \
                 patch('sys.argv',['run','--recipe',str(path),'--output',tmp,'--commit','9'*40]):
                main()
                self.assertEqual(os.environ['JAX_PLATFORMS'],'cuda,cpu')
                self.assertEqual(os.environ['JAX_ENABLE_X64'],'true')
                self.assertEqual(os.environ['BSFM_EXPERIMENTAL_CUDA'],'1')
                execute.assert_called_once()


if __name__=='__main__':unittest.main()
