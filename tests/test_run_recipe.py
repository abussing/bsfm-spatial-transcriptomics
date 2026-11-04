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
        for model in ('deep','flat'):
            with self.subTest(model=model),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp); c=setup(root/'fixture','deep')
                payload=root/'input';payload.write_bytes(b'authenticated synthetic fixture')
                files={'fixture':dict(path='input',**file_record(payload))}
                recipe=dict(schema='bsfm.sampler-run.v1',backend='cpu',model=model,
                    chain_id='chain',factor_ids=list(c.target.factor_ids),seed=491,files=files,
                    dataset_recipe=None,gpu_runtime=None,phases=[
                        dict(run_id='bridge',warmup_steps=20,sweeps=1,save_every=2),
                        dict(run_id='production',warmup_steps=20,sweeps=2,save_every=2)])
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
                    changed=copy.deepcopy(recipe);changed['phases'][1]['sweeps']=3
                    path.write_text(json.dumps(changed))
                    with self.assertRaises(ValueError):run_recipe(path,root/'outputs',commit='9'*40)

    def test_repository_and_recipe_rejections(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError,'tracked'):
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
