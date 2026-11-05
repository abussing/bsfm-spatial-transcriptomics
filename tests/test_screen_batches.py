import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from test_spatial_screen import fixture
from bsfm.preprocessing.dataset import write_dataset,file_hash
from bsfm.preprocessing.spatial_screen import screen_sample,screen_batched


class ScreenBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.data,self.meta,self.spec=fixture()
        self.data['group_names']=self.data['group_names'].astype('U6')
        self.data['group_names'][16:]='second'
        self.spec['groups']=['type','second']
        write_dataset(self.root/'data',self.data,self.meta,sources=[dict(path='synthetic',sha256='0'*64)])
        self.recipe=self.root/'recipe.json';self.recipe.write_text(json.dumps(self.spec))
        self.args=(self.root/'data',file_hash(self.root/'data/dataset.json'),self.recipe,self.root/'checkpoints')

    def run_batches(self,workers=1):
        return screen_batched(*self.args,batch_size=1,workers=workers,output=self.root/'result.json')

    def test_parallel_exact_and_completed_resume(self):
        direct=screen_sample(self.data,self.meta,**self.spec)
        result=self.run_batches(workers=2)
        self.assertEqual(direct,{k:result[k] for k in direct})
        before={p.name:p.read_bytes() for p in (self.root/'checkpoints').glob('*.json')}
        with patch('bsfm.preprocessing.spatial_screen.screen_sample',side_effect=AssertionError('replayed')):
            self.assertEqual(result,self.run_batches())
        self.assertEqual(before,{p.name:p.read_bytes() for p in (self.root/'checkpoints').glob('*.json')})

    def test_interrupted_batch_resume_and_tampering(self):
        calls=[]
        def fail_second(*args,**kwargs):
            calls.append(kwargs['genes'])
            if len(calls)==2:raise RuntimeError('simulated interruption')
            return screen_sample(*args,**kwargs)
        with patch('bsfm.preprocessing.spatial_screen.screen_sample',side_effect=fail_second):
            with self.assertRaises(RuntimeError):self.run_batches()
        self.assertEqual(len(list((self.root/'checkpoints').glob('batch-*.json'))),1)
        with patch('bsfm.preprocessing.spatial_screen.screen_sample',wraps=screen_sample) as fit:
            result=self.run_batches();self.assertEqual(fit.call_count,1)
        self.assertEqual(result['rows'],screen_sample(self.data,self.meta,**self.spec)['rows'])
        batch=self.root/'checkpoints/batch-000000.json';record=json.loads(batch.read_text())
        record['report']['rows'][0]['spatial_fraction']=.123;batch.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'checksum'):self.run_batches()

    def test_changed_recipe_and_active_lock_rejected(self):
        self.run_batches()
        self.spec['config']['seed']=99;self.recipe.write_text(json.dumps(self.spec))
        with self.assertRaisesRegex(ValueError,'Existing output differs'):self.run_batches()
        (self.root/'checkpoints/.lock').mkdir()
        with self.assertRaises(FileExistsError):self.run_batches()


if __name__=='__main__':unittest.main()
