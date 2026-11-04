import csv
import json
import math
from pathlib import Path
import unittest
import numpy as np
from bsfm.preprocessing.gene_selection import expression_eligible,select_spatial_genes
from bsfm.preprocessing.normalization import log_library_size,center_from_training

ROOT=Path(__file__).resolve().parents[1]


class DatasetPreprocessingTests(unittest.TestCase):
    def test_recovered_91_gene_regression(self):
        with (ROOT/'docs/recovery/gene-panel-20261104/EXPANDED_GP_ANIMAL_SUMMARY.csv').open() as f:
            rows=list(csv.DictReader(f))
        recipe=json.loads((ROOT/'config/preprocessing/johnston-gene-selection.json').read_text())
        result=select_spatial_genes(rows,**recipe['selection'])
        self.assertEqual(result['genes'],json.loads((ROOT/'config/preprocessing/modeling-panel.json').read_text())['genes'])
        # Neither genotype nor auxiliary predictive scores may influence selection.
        for r in rows:r.update(genotype='arbitrary',heldout_gain=-1e30)
        self.assertEqual(result,select_spatial_genes(rows,**recipe['selection']))

    def test_same_type_recurrence_and_exact_threshold(self):
        rows=[dict(gene='cross',celltype='a',animal='one',spatial_fraction=.5),
              dict(gene='cross',celltype='b',animal='two',spatial_fraction=.5),
              dict(gene='keep',celltype='a',animal='one',spatial_fraction=.1),
              dict(gene='keep',celltype='a',animal='two',spatial_fraction=.2)]
        kwargs=dict(spatial_fraction_threshold=.1,minimum_animals=2,allowed_celltypes=['a','b'])
        self.assertEqual(select_spatial_genes(rows,**kwargs)['genes'],['keep'])
        with self.assertRaises(ValueError):select_spatial_genes(rows+[rows[0]],**kwargs)
        with self.assertRaises(ValueError):select_spatial_genes([dict(rows[0],spatial_fraction=1.1)],**kwargs)

    def test_expression_screen_joint_criteria(self):
        y=np.array([[0]*7+[2]*3,[0]*8+[2]*2,[1]*10,[0]*7+[.2]*3],float)
        r=expression_eligible(y,minimum_detection=.3,minimum_q90=1)
        np.testing.assert_array_equal(r['eligible'],[True,False,False,False])

    def test_library_scale_and_base(self):
        x=np.array([[1,4],[3,4]],float)
        y,r=log_library_size(x,target_sum=8,log_base=2)
        np.testing.assert_allclose(y,np.log2([[3,5],[7,5]]),rtol=1e-15)
        np.testing.assert_allclose(np.expm1(y*math.log(2)).sum(axis=0),8)
        with self.assertRaises(ValueError):log_library_size(y,target_sum=8,log_base=2)
        with self.assertRaises(ValueError):log_library_size(np.zeros((2,2)),target_sum=8,log_base=2)

    def test_centering_uses_only_training_and_does_not_mutate(self):
        y=np.array([[2,4,99,10,14,101]],float);before=y.copy()
        groups=np.array(['a','a','a','b','b','b']);train=np.array([1,1,0,1,1,0],bool)
        out,record=center_from_training(y,groups,train)
        np.testing.assert_array_equal(out,[[-1,1,96,-2,2,89]])
        np.testing.assert_array_equal(record['means'],[[3,12]])
        np.testing.assert_array_equal(y,before)
        y[:,~train]=-999
        _,changed=center_from_training(y,groups,train)
        np.testing.assert_array_equal(changed['means'],record['means'])
        with self.assertRaises(ValueError):center_from_training(y,groups,np.array([1,1,0,0,0,0],bool))


if __name__=='__main__':unittest.main()
