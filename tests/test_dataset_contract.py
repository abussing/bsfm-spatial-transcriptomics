import copy
import tempfile
from pathlib import Path
import unittest
import numpy as np
from bsfm.preprocessing.dataset import validate,write_dataset,load_dataset,file_hash,prepare_response
from bsfm.sampler.contracts import validate_input


def fixture():
    data=dict(expression=np.array([[1,2,9,10,11,18],[4,8,90,20,22,180]],dtype=np.float64),
              coordinates=np.array([[0,0],[1,1],[2,0],[3,1],[4,0],[5,1]],dtype=np.float64),
              gene_names=np.array(['gene-b','gene-a']),cell_names=np.array(['c0','c1','c2','c3','c4','c5']),
              group_names=np.array(['X','X','X','Y','Y','Y']),sample_names=np.array(['sample']*6),
              animal_names=np.array(['']*6),source_row_indices=np.arange(6))
    meta=dict(schema='bsfm.dataset.v1',dataset_id='synthetic',animal_identity_known=False,
              coordinate_units='source_native',normalization=dict(response='uncentered_normalized',
              method='imported_test_fixture',units='arbitrary_test_units',population='all synthetic cells',
              evidence='synthetic test only'))
    return data,meta


class DatasetContractTests(unittest.TestCase):
    def test_portable_roundtrip_and_tamper(self):
        d,m=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'bundle'
            write_dataset(root,d,m,sources=[dict(path='synthetic',sha256='0'*64)])
            expected=file_hash(root/'dataset.json')
            restored,_=load_dataset(root,expected_manifest_sha256=expected)
            for k in d:np.testing.assert_array_equal(d[k],restored[k])
            with self.assertRaises(FileExistsError):write_dataset(root,d,m,sources=[dict(path='synthetic',sha256='0'*64)])
            with (root/'dataset.npz').open('ab') as f:f.write(b'tampered')
            with self.assertRaises(ValueError):load_dataset(root,expected_manifest_sha256=expected)

    def test_no_fabricated_animals_or_duplicate_cells(self):
        d,m=fixture();d['animal_names']=np.array(['fake']*6)
        with self.assertRaises(ValueError):validate(d,m)
        d,m=fixture();d['cell_names'][1]=d['cell_names'][0]
        with self.assertRaises(ValueError):validate(d,m)

    def test_preparation_keeps_names_order_scale_and_training_only_means(self):
        d,m=fixture();original=copy.deepcopy(d)
        args=dict(sample='sample',groups=['Y','X'],genes=['gene-a','gene-b'],
                  training_cells=['c0','c1','c3','c4'],heldout_cells=['c2','c5'])
        train,test,r=prepare_response(d,m,**args)
        np.testing.assert_array_equal(train['cell_names'],['c3','c4','c0','c1'])
        np.testing.assert_array_equal(train['cell_id'],[0,0,1,1])
        np.testing.assert_array_equal(train['Y'],[[-1,1,-2,2],[-.5,.5,-.5,.5]])
        np.testing.assert_array_equal(test['Y'],[[159,84],[7.5,7.5]])
        self.assertEqual(r['coordinate_transform']['scale'],5)
        validate_input(train)
        for k in d:np.testing.assert_array_equal(d[k],original[k])
        d['expression'][:,[2,5]]+=1234
        changed,_,r2=prepare_response(d,m,**args)
        np.testing.assert_array_equal(changed['Y'],train['Y'])
        self.assertEqual(r2['centering'],r['centering'])

    def test_split_and_population_failures(self):
        d,m=fixture()
        args=dict(sample='sample',groups=['X','Y'],genes=['gene-a'],training_cells=['c0'],heldout_cells=['c5'])
        with self.assertRaises(ValueError):prepare_response(d,m,**args)
        args.update(training_cells=['c0','c3'],heldout_cells=['c0'])
        with self.assertRaises(ValueError):prepare_response(d,m,**args)
        args.update(heldout_cells=['missing'])
        with self.assertRaises(ValueError):prepare_response(d,m,**args)


if __name__=='__main__':unittest.main()
