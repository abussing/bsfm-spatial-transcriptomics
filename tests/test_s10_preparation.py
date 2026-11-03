"""Mechanical identity failures; no GP fitting or response transformations."""
import copy
import unittest
import numpy as np
from bsfm.initialization.s10_preparation import validate_model, identities, check_join, COUNTS
from bsfm.initialization.s10_gpinit_gate import validate_provenance, CONFIG_SHA


def fixture():
    n=9422
    return dict(Y=np.zeros((91,n)),slocs=np.zeros((n,2)),
                cell_id=np.repeat(np.arange(3),COUNTS),
                source_row_indices=np.arange(n,dtype=np.int64),
                cell_names=np.array([f'cell-{i}' for i in range(n)]),
                gene_names=np.array([f'gene-{i}' for i in range(91)]),
                cell_type_names=np.array(['MIC','AST','OGC']))


class PreparationTests(unittest.TestCase):
    def setUp(self):
        self.data=fixture();self.expected=identities(self.data);self.genes=self.data['gene_names'].copy()

    def test_exact_full_cell_identity(self):
        validate_model(self.data,self.expected,self.genes)

    def test_no_mutation(self):
        validate_model(self.data,self.expected,self.genes)
        self.assertEqual(identities(self.data),self.expected)

    def test_historical_half_population_rejected(self):
        self.data['Y']=self.data['Y'][:,:4712]
        with self.assertRaisesRegex(ValueError,'full-cell'):validate_model(self.data,self.expected,self.genes)

    def test_response_corruption(self):
        self.data['Y'][0,0]=1e-10
        with self.assertRaisesRegex(ValueError,'array/value'):validate_model(self.data,self.expected,self.genes)

    def test_gene_order(self):
        self.data['gene_names']=self.data['gene_names'][::-1]
        with self.assertRaisesRegex(ValueError,'panel'):validate_model(self.data,self.expected,self.genes)

    def test_type_order(self):
        self.data['cell_id'][0]=2
        with self.assertRaisesRegex(ValueError,'Type block'):validate_model(self.data,self.expected,self.genes)

    def test_source_row_order(self):
        self.data['source_row_indices'][[0,1]]=self.data['source_row_indices'][[1,0]]
        with self.assertRaisesRegex(ValueError,'row order'):validate_model(self.data,self.expected,self.genes)

    def test_duplicate_or_fabricated_ids(self):
        for replacement in ('cell-1','raw-row-0'):
            data=copy.deepcopy(self.data);data['cell_names'][0]=replacement
            with self.assertRaises(ValueError):validate_model(data,self.expected,self.genes)

    def test_nonfinite(self):
        self.data['Y'][0,0]=np.nan
        with self.assertRaisesRegex(ValueError,'Invalid response'):validate_model(self.data,self.expected,self.genes)

    def test_mesh_permutation_rejected(self):
        xy=np.column_stack((np.arange(9422,dtype=float),np.arange(9422,dtype=float)))
        self.data['slocs']=xy/9421
        mesh=dict(slocs=self.data['slocs'][::-1],source_rows=self.data['source_row_indices'],cell_type=self.data['cell_id'])
        with self.assertRaisesRegex(ValueError,'Mesh/model order'):check_join(self.data,xy,mesh)


class ProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.producer=dict(baseline_commit='0c5bed151def7c2ae429c0bc894cdb3aead96251',generating_commit=None)
        self.contract=dict(producer=self.producer)
        self.environment=dict(authenticated_test_identity='expected')
        self.cert=dict(provenance=dict(config_sha256=CONFIG_SHA,environment=copy.deepcopy(self.environment),
                       accepted_code_commit=self.producer['baseline_commit'],preparation_producer=copy.deepcopy(self.producer)))

    def test_committed_producer_and_expected_bindings(self):
        validate_provenance(self.cert,self.contract,self.environment)

    def test_recorded_configuration_corruption(self):
        self.cert['provenance']['config_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'configuration'):validate_provenance(self.cert,self.contract,self.environment)

    def test_recorded_environment_corruption(self):
        self.cert['provenance']['environment']['authenticated_test_identity']='changed'
        with self.assertRaisesRegex(ValueError,'environment'):validate_provenance(self.cert,self.contract,self.environment)

    def test_recorded_commit_corruption(self):
        self.cert['provenance']['accepted_code_commit']='0'*40
        with self.assertRaisesRegex(ValueError,'code commit'):validate_provenance(self.cert,self.contract,self.environment)

    def test_recorded_preparation_producer_corruption(self):
        self.cert['provenance']['preparation_producer']['generating_commit']='0'*40
        with self.assertRaisesRegex(ValueError,'preparation producer'):validate_provenance(self.cert,self.contract,self.environment)


if __name__=='__main__':unittest.main()
