"""Synthetic H5AD contract tests; no historical code or real expression used."""

import csv
import json
import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np

from bsfm.preprocessing.raw_preflight import (
    ContractError, audit_h5ad, count_totals, load_registry, main, sha256_file, write_reports,
)


def string_array(group, key, values):
    group.create_dataset(key, data=np.array(values, dtype=object), dtype=h5py.string_dtype())


def categorical(group, key, values, reverse=False):
    categories = sorted(set(values), reverse=reverse)
    node = group.create_group(key)
    node.attrs['encoding-type'] = 'categorical'
    node.attrs['encoding-version'] = '0.2.0'
    string_array(node, 'categories', categories)
    node.create_dataset('codes', data=np.array([categories.index(v) for v in values], dtype=np.int16))


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'tiny.h5ad'
        self.ledger = self.root / 'history.csv'
        self.registry = load_registry()['sections']
        self.counts = np.zeros((76, 300), dtype=np.float64)
        for i in range(19):
            self.counts[4*i:4*i+4, 0] = np.array([1, 2, 4, 8]) + i
        with self.ledger.open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['section','all_cell_count','glial_count'])
            writer.writeheader()
            writer.writerows({'section':r['section'],'all_cell_count':4,'glial_count':3} for r in self.registry)
        self.fixture()

    def fixture(self, storage='dense', reverse_categories=False):
        with h5py.File(self.path, 'w') as f:
            f.attrs.update({'encoding-type':'anndata','encoding-version':'0.1.0'})
            for name, ids in [('obs',[f'cell_{i}' for i in range(76)]), ('var',[f'gene_{i}' for i in range(300)])]:
                node = f.create_group(name)
                node.attrs.update({'_index':'_index','encoding-type':'dataframe','encoding-version':'0.2.0'})
                string_array(node, '_index', ids)
            for field in ['sample','gen_fine']:
                categorical(f['obs'], field, [r[field] for r in self.registry for _ in range(4)], reverse_categories)
            categorical(f['obs'], 'cluster_coarse', ['Mic','AST','OGC','Neuron']*19, reverse_categories)
            f.create_dataset('obsm/spatial', data=np.arange(152).reshape(76,2))
            f.create_group('layers')
            if storage == 'dense':
                f.create_dataset('layers/RNA', data=self.counts, chunks=(3,300))
            else:
                node = f.create_group('layers/RNA')
                node.attrs.update({'encoding-type':storage,'encoding-version':'0.1.0','shape':self.counts.shape})
                matrix = self.counts if storage == 'csr_matrix' else self.counts.T
                data, indices, indptr = [], [], [0]
                for row in matrix:
                    cols = np.flatnonzero(row)
                    data.extend(row[cols]); indices.extend(cols); indptr.append(len(data))
                node.create_dataset('data',data=np.array(data,dtype=np.float64))
                node.create_dataset('indices',data=np.array(indices,dtype=np.int64))
                node.create_dataset('indptr',data=np.array(indptr,dtype=np.int64))

    def audit(self, **kwargs):
        return audit_h5ad(self.path, historical_ledger=self.ledger, chunk_rows=kwargs.pop('chunk_rows',2), **kwargs)

    def test_dense_and_sparse_equivalence(self):
        reference, exclusions = self.audit()
        self.assertEqual(reference['status'],'pass')
        self.assertEqual(reference['proposed_common_depth'],3.0)
        self.assertEqual(exclusions,[])
        self.assertEqual(reference['sections'][0]['total_q25'],1.75)
        for storage in ['csr_matrix','csc_matrix']:
            with self.subTest(storage=storage):
                self.fixture(storage)
                measured, _ = self.audit()
                self.assertEqual(measured['sections'],reference['sections'])
                self.assertEqual(measured['aggregate'],reference['aggregate'])
                self.assertEqual(measured['proposed_common_depth'],3.0)

    def test_duplicate_identifiers(self):
        for axis in ['obs','var']:
            with self.subTest(axis=axis):
                self.fixture()
                with h5py.File(self.path,'r+') as f:
                    f[f'{axis}/_index'][1] = f[f'{axis}/_index'][0]
                with self.assertRaisesRegex(ContractError,'duplicate identifiers'):
                    self.audit()

    def test_invalid_counts_excluded_without_rounding(self):
        for storage in ['dense','csr_matrix','csc_matrix']:
            with self.subTest(storage=storage):
                self.counts[0,0],self.counts[1,0],self.counts[2,0] = -1,1.5,np.nan
                self.fixture(storage)
                audit, excluded = self.audit()
                self.assertEqual(audit['status'],'review_required')
                self.assertEqual(audit['sections'][0]['eligible_cells'],1)
                self.assertEqual(audit['sections'][0]['total_median'],8)
                self.assertEqual(audit['counts']['invalid_value_counts'],{'negative_count':1,'noninteger_count':1,'nonfinite_count':1})
                self.assertEqual([r['source_row'] for r in excluded],[0,1,2])

    def test_zero_cells_excluded_before_median(self):
        self.counts[0,:] = 0
        self.fixture()
        audit, excluded = self.audit()
        row = audit['sections'][0]
        self.assertEqual(row['eligible_cells'],3)
        self.assertEqual(row['zero_total_cells'],1)
        self.assertEqual(row['total_median'],4)
        self.assertEqual(row['eligible_MIC'],0)
        self.assertTrue(row['historical_counts_match'])
        self.assertEqual(excluded[0]['reasons'],'zero_total')

    def test_missing_required_metadata(self):
        for key in ['obs/sample','obs/gen_fine','obs/cluster_coarse','obsm/spatial','layers/RNA']:
            with self.subTest(key=key):
                self.fixture()
                with h5py.File(self.path,'r+') as f: del f[key]
                with self.assertRaisesRegex(ContractError,'Missing required'):
                    self.audit()

    def test_missing_values_and_spatial_exclusions(self):
        with h5py.File(self.path,'r+') as f:
            f['obs/cluster_coarse/codes'][0] = -1
            f['obs/sample/codes'][1] = -1
            del f['obsm/spatial']
            coords = np.zeros((76,2)); coords[2,0] = np.inf
            f.create_dataset('obsm/spatial',data=coords)
        audit, excluded = self.audit()
        self.assertEqual(audit['status'],'review_required')
        self.assertEqual(audit['aggregate']['eligible_cells'],73)
        self.assertEqual(len(excluded),3)

    def test_two_s12_sections_and_category_reordering(self):
        reference, _ = self.audit()
        self.fixture(reverse_categories=True)
        audit, _ = self.audit()
        self.assertEqual(audit['sections'],reference['sections'])
        s12 = [r for r in audit['sections'] if r['section'].startswith('S12__')]
        self.assertEqual(len(s12),2)
        self.assertEqual([r['all_cells'] for r in s12],[4,4])
        self.assertEqual([r['total_median'] for r in s12],[15,16])
        self.assertNotEqual(s12[0]['selected_cell_order_sha256'],s12[1]['selected_cell_order_sha256'])

    def test_deterministic_outputs_and_read_only(self):
        before = sha256_file(self.path)
        for i in range(2):
            audit, excluded = self.audit()
            write_reports(audit, excluded, self.root/f'out{i}')
        for file in (self.root/'out0').iterdir():
            self.assertEqual(file.read_bytes(),(self.root/'out1'/file.name).read_bytes())
        self.assertEqual(before,sha256_file(self.path))
        with self.assertRaises(FileExistsError):
            write_reports(audit, excluded, self.root/'out0')

    def test_missing_section_withholds_depth(self):
        self.counts[:4,:] = 0
        self.fixture()
        audit, _ = self.audit()
        self.assertEqual(audit['status'],'fail')
        self.assertIsNone(audit['proposed_common_depth'])

    def test_history_mismatch_is_reported(self):
        independent, independent_excluded = audit_h5ad(self.path)
        content = self.ledger.read_text().replace(',4,3',',5,3',1)
        self.ledger.write_text(content)
        audit, excluded = self.audit()
        self.assertEqual(audit['status'],'review_required')
        self.assertEqual(audit['sections'][0]['historical_all_delta'],-1)
        self.assertEqual(audit['proposed_common_depth'],3)
        self.assertEqual(audit['proposed_common_depth'],independent['proposed_common_depth'])
        self.assertEqual(audit['aggregate'],independent['aggregate'])
        self.assertEqual(excluded,independent_excluded)

    def test_optional_history_preserves_canonical_audit(self):
        compared, compared_excluded = self.audit()
        self.ledger.unlink()
        independent, excluded = audit_h5ad(self.path,chunk_rows=2)
        self.assertEqual(independent['status'],'pass')
        self.assertIsNone(independent['historical_ledger'])
        self.assertIsNone(independent['policy']['comparison_population'])
        self.assertEqual(independent['aggregate'],compared['aggregate'])
        self.assertEqual(independent['proposed_common_depth'],compared['proposed_common_depth'])
        self.assertEqual(excluded,compared_excluded)
        for actual, historical in zip(independent['sections'],compared['sections']):
            for field in actual:
                if field.startswith('historical_'):
                    self.assertIsNone(actual[field])
                else:
                    self.assertEqual(actual[field],historical[field])

    def test_cli_without_history(self):
        self.ledger.unlink()
        output = self.root/'independent_cli'
        self.assertEqual(main([str(self.path),'--output-dir',str(output)]),0)
        audit = json.loads((output/'audit.json').read_text())
        self.assertIsNone(audit['historical_ledger'])
        self.assertEqual(audit['proposed_common_depth'],3)
        with (output/'sections.csv').open(newline='') as stream:
            self.assertTrue(all(r['historical_counts_match']=='' for r in csv.DictReader(stream)))
        self.assertIn('historical comparison not requested',(output/'summary.md').read_text())

    def test_shape_panel_and_sparse_integrity(self):
        with h5py.File(self.path,'r+') as f:
            del f['layers/RNA']
            f.create_dataset('layers/RNA',data=np.ones((76,299)))
        with self.assertRaisesRegex(ContractError,'shape'):
            self.audit()
        self.fixture('csr_matrix')
        with h5py.File(self.path,'r+') as f:
            f['layers/RNA/indptr'][-1] += 1
        with self.assertRaisesRegex(ContractError,'indptr'):
            self.audit()
        self.fixture()
        with h5py.File(self.path,'r+') as f:
            del f['var/_index']; string_array(f['var'],'_index',[f'g{i}' for i in range(299)])
        with self.assertRaisesRegex(ContractError,'exactly 300'):
            self.audit()

    def test_sparse_chunk_boundary_and_duplicate_rejection(self):
        # A long CSC column crosses multiple entry-read boundaries; an empty
        # column must not shift cell assignment. CSR and dense sums agree too.
        self.counts = np.zeros((1001,300))
        self.counts[:,0] = np.arange(1001)
        self.counts[:,2] = 3
        for storage in ['dense','csr_matrix','csc_matrix']:
            with self.subTest(storage=storage):
                self.fixture(storage)
                with h5py.File(self.path,'r') as f:
                    totals, bad, _ = count_totals(f['layers/RNA'], self.counts.shape, 1)
                np.testing.assert_array_equal(totals,np.arange(1001)+3)
                self.assertFalse(any(v.any() for v in bad.values()))
        with h5py.File(self.path,'r+') as f:
            f['layers/RNA/indices'][1] = f['layers/RNA/indices'][0]
        with h5py.File(self.path,'r') as f:
            with self.assertRaisesRegex(ContractError,'duplicate or unsorted'):
                count_totals(f['layers/RNA'], self.counts.shape, 1)

    def test_unsafe_precision_is_not_rounded(self):
        self.counts[0,0],self.counts[0,1] = 2**53,1
        self.fixture()
        audit, excluded = self.audit()
        self.assertEqual(audit['aggregate']['reason_counts']['unsafe_total'],1)
        self.assertEqual(excluded[0]['reasons'],'unsafe_total')

    def test_unknown_section_withholds_depth(self):
        with h5py.File(self.path,'r+') as f:
            f['obs/gen_fine/codes'][0] = (int(f['obs/gen_fine/codes'][0])+1)%19
        audit, _ = self.audit()
        self.assertIsNone(audit['proposed_common_depth'])
        self.assertEqual(audit['status'],'fail')

    def test_cli_and_no_overwrite(self):
        output = self.root/'cli'
        args = [str(self.path),'--historical-ledger',str(self.ledger),'--output-dir',str(output),'--chunk-rows','1']
        self.assertEqual(main(args),0)
        self.assertEqual(json.loads((output/'audit.json').read_text())['proposed_common_depth'],3)
        self.assertEqual(main(args),2)


if __name__ == '__main__':
    unittest.main()
