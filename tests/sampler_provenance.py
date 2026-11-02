"""Portable lookup of frozen source identities and Python-3.12 AST fingerprints."""
import ast
import copy
import csv
import hashlib
from pathlib import Path, PureWindowsPath

ROOT = Path(__file__).resolve().parents[1]
SELECTED_ROOT = PureWindowsPath(
    r'D:\johnston_brain\run_bundles\bsfm_l4_k20_cell50_fmesher_20261026_v1\code\sampler')


def selected_source_record(filename, ledger=None):
    """Select the exact nominated F path, never an ambiguous basename match.

    The caller's physical source root can be on another machine. It must still
    authenticate the selected file's bytes and hash before executing any AST.
    """
    if not filename or '/' in filename or '\\' in filename or filename in ('.', '..'):
        raise ValueError('A single source filename is required')
    ledger = ledger or ROOT/'docs/recovery/BSFM_SAMPLER_SOURCES.csv'
    expected = str(SELECTED_ROOT/filename)
    with Path(ledger).open(encoding='utf-8', newline='') as stream:
        matches = [r for r in csv.DictReader(stream) if r['source_path'] == expected]
    if len(matches) != 1:
        raise ValueError('Expected exactly one selected source identity: '+expected)
    return matches[0]


def body_ast_sha256(node):
    """Serialize in the recorded 3.12 schema without erasing semantic fields.

    Python 3.11 lacks the empty type_params field added in 3.12. Populate only
    that absent field on a copy. Existing type parameters and all body nodes
    remain part of the hash. Source-file SHA-256 checks remain independent.
    """
    tree = copy.deepcopy(ast.Module(body=node.body, type_ignores=[]))
    for child in ast.walk(tree):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if 'type_params' not in child._fields:
                child._fields = (*child._fields, 'type_params')
                child.type_params = []
    return hashlib.sha256(ast.dump(tree, include_attributes=False).encode()).hexdigest()
