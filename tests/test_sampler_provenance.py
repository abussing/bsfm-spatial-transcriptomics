"""Keep provenance strict across path and AST schema differences."""
import ast
import csv
import tempfile
import unittest
from pathlib import Path

from sampler_provenance import SELECTED_ROOT, selected_source_record, body_ast_sha256


class ProvenanceTests(unittest.TestCase):
    def test_exact_source_selected_despite_same_basename(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory)/'sources.csv'
            with ledger.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=['source_path', 'sha256'])
                writer.writeheader()
                writer.writerows([
                    {'source_path': str(SELECTED_ROOT/'target.py'), 'sha256': 'selected'},
                    {'source_path': r'C:\other\target.py', 'sha256': 'wrong'}])
            self.assertEqual(selected_source_record('target.py', ledger)['sha256'], 'selected')

    def test_missing_and_duplicate_source_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory)/'sources.csv'
            row = str(SELECTED_ROOT/'target.py')+',identity\n'
            for rows in ('', row+row):
                ledger.write_text('source_path,sha256\n'+rows, encoding='utf-8')
                with self.assertRaises(ValueError):
                    selected_source_record('target.py', ledger)

    def test_path_instead_of_filename_rejected(self):
        for name in ('../target.py', r'other\target.py', '', '..'):
            with self.assertRaises(ValueError):
                selected_source_record(name)

    def test_311_and_312_empty_type_parameters_match_without_mutation(self):
        node = ast.parse('def outer():\n def inner():\n  return 1\n return inner()\n').body[0]
        inner = node.body[0]
        inner._fields = tuple(f for f in inner._fields if f != 'type_params')
        if hasattr(inner, 'type_params'):
            del inner.type_params
        before = ast.dump(node)
        old = body_ast_sha256(node)
        self.assertEqual(ast.dump(node), before)
        inner._fields = (*inner._fields, 'type_params')
        inner.type_params = []
        self.assertEqual(body_ast_sha256(node), old)

    def test_semantic_changes_still_change_hash(self):
        a = ast.parse('def outer():\n def inner():\n  return 1\n').body[0]
        b = ast.parse('def outer():\n def inner():\n  return 2\n').body[0]
        self.assertNotEqual(body_ast_sha256(a), body_ast_sha256(b))
        before = body_ast_sha256(a)
        child = a.body[0]
        if 'type_params' not in child._fields:
            child._fields = (*child._fields, 'type_params')
        child.type_params = [ast.Name(id='T', ctx=ast.Load())]
        self.assertNotEqual(body_ast_sha256(a), before)


if __name__ == '__main__':
    unittest.main()
