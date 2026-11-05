import copy
import unittest
from bsfm.preprocessing.gene_selection import select_single_sample_genes


class SingleSampleSelectionTests(unittest.TestCase):
    def setUp(self):
        self.rows=[dict(sample='s',gene=g,celltype=t,status='FIT',animal=None,spatial_fraction=v)
                   for g,t,v in [('g1','a',.1),('g1','b',.01),('g2','a',.09),('g2','b',.09)]]
        self.args=dict(sample='s',spatial_fraction_threshold=.1,allowed_celltypes=['a','b'])

    def test_union_threshold_and_no_animal_claim(self):
        r=select_single_sample_genes(self.rows,**self.args)
        self.assertEqual(r['genes'],['g1'])
        self.assertFalse(r['cross_animal_recurrence_assessed'])
        changed=copy.deepcopy(self.rows)
        for row in changed:row.update(animal='unknown',heldout_gain=1000)
        self.assertEqual(r,select_single_sample_genes(changed,**self.args))

    def test_incomplete_duplicate_mixed_or_invalid_rejected(self):
        for rows in [self.rows[:-1],self.rows+[self.rows[0]],[]]:
            with self.assertRaises(ValueError):select_single_sample_genes(rows,**self.args)
        for field,value in [('sample','other'),('celltype','other'),('status','FAILED'),('spatial_fraction',float('nan'))]:
            rows=copy.deepcopy(self.rows);rows[0][field]=value
            with self.assertRaises(ValueError):select_single_sample_genes(rows,**self.args)

    def test_explicit_ineligibility_excludes(self):
        rows=copy.deepcopy(self.rows)
        rows[0].update(status='EXPRESSION_INELIGIBLE',spatial_fraction=None)
        self.assertEqual(select_single_sample_genes(rows,**self.args)['genes'],[])


if __name__=='__main__':unittest.main()
