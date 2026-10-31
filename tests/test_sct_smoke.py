"""Transport, selection and gate tests; R fits are the separate integration gate."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import h5py
import numpy as np

from bsfm.preprocessing import sct_smoke as smoke
from bsfm.preprocessing.raw_preflight import ContractError


class SmokeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_binary_transport_orientation_and_hashes(self):
        x = np.array([[1, 2, 3], [4, 5, 6]])
        meta = smoke.write_input(self.root/'input', x, ['g1','g2','g3'], ['c1','c2'], {})
        payload = np.fromfile(self.root/'input/counts.f64', dtype='<f8')
        np.testing.assert_array_equal(payload.reshape((3,2),order='F'), x.T)
        self.assertEqual(meta['shape'], [3,2])
        self.assertEqual(meta['files'][0]['sha256'], smoke.sha256_file(self.root/'input/counts.f64'))

    def test_invalid_counts_and_identifiers_fail(self):
        for x, genes, cells in [
            ([[1,-1],[1,1]], ['a','b'], ['c','d']),
            ([[1,.5],[1,1]], ['a','b'], ['c','d']),
            ([[1,np.nan],[1,1]], ['a','b'], ['c','d']),
            ([[0,0],[1,1]], ['a','b'], ['c','d']),
            ([[1,1],[1,1]], ['a','a'], ['c','d']),
            ([[1,1],[1,1]], ['a','b'], ['c','c']),
        ]:
            with self.subTest(x=x,genes=genes,cells=cells), self.assertRaises(ContractError):
                smoke.write_input(self.root/'invalid', x, genes, cells, {})
        self.assertFalse((self.root/'invalid').exists())

    def test_selected_dense_csr_csc_preserves_rows_and_genes(self):
        x = np.array([[0,2,0],[3,0,4],[0,0,5],[6,7,0]],dtype=float)
        rows = np.array([1,3])
        with h5py.File(self.root/'fixture.h5', 'w') as f:
            dense=f.create_dataset('dense',data=x)
            np.testing.assert_array_equal(smoke.selected_counts(dense,rows,3),x[rows])
            for name, major in [('csr_matrix',x),('csc_matrix',x.T)]:
                group=f.create_group(name);group.attrs['encoding-type']=name
                values=[]; indices=[]; pointers=[0]
                for row in major:
                    ix=np.flatnonzero(row)
                    indices.extend(ix);values.extend(row[ix]);pointers.append(len(values))
                for key,value in [('data',values),('indices',indices),('indptr',pointers)]:
                    group.create_dataset(key,data=value)
                np.testing.assert_array_equal(smoke.selected_counts(group,rows,3),x[rows])

    def test_synthetic_determinism_and_independent_common_depth(self):
        first=smoke.synthetic_inputs(self.root/'one')
        second=smoke.synthetic_inputs(self.root/'two')
        self.assertEqual(first,second)
        self.assertEqual(first['common_depth'],min(first['medians']))
        self.assertNotEqual(*first['medians'])
        for name in ['synthetic-A','synthetic-B']:
            for filename in ['counts.f64','genes.json','cells.json','input.json']:
                self.assertEqual((self.root/'one'/name/filename).read_bytes(),(self.root/'two'/name/filename).read_bytes())

    def test_failed_synthetic_gate_never_reads_real_source(self):
        env=self.root/'env';env.mkdir();(env/'source-lock.json').write_text('{}')
        args=['sct_smoke','--environment',str(env),'--output-dir',str(self.root/'run'),
              '--raw-source','DO_NOT_OPEN.h5ad']
        with patch('sys.argv',args), patch.object(smoke,'run_r',side_effect=ContractError('synthetic failed')), patch.object(smoke,'s00_input') as real:
            with self.assertRaisesRegex(ContractError,'synthetic failed'): smoke.main()
            real.assert_not_called()
        self.assertEqual(json.loads((self.root/'run/run-manifest.json').read_text())['status'],'fail')

    def test_mismatched_repeats_never_read_real_source(self):
        env=self.root/'env';env.mkdir();(env/'source-lock.json').write_text('{}')
        args=['sct_smoke','--environment',str(env),'--output-dir',str(self.root/'run'),
              '--raw-source','DO_NOT_OPEN.h5ad']
        returns=[{'report':{'semantic_sha256':{'counts':'a'}}},{'report':{'semantic_sha256':{'counts':'b'}}}]
        with patch('sys.argv',args), patch.object(smoke,'run_r',side_effect=returns), patch.object(smoke,'s00_input') as real:
            with self.assertRaisesRegex(ContractError,'Fresh-session repeat differs'):smoke.main()
            real.assert_not_called()


if __name__ == '__main__':
    unittest.main()
