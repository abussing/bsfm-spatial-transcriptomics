# Portable sampler source/port validation

The first Linux job [22012327](HPC_CPU_VALIDATION_22012327.json) failed its
Windows-fixture gate. Preserve that result and the committed fixtures. The
sampler formulas, priors, gradients, RNG calls and tolerances are unchanged.

## Corrections to validation tooling

- Source ledgers name exact historical Windows paths. Reference acquisition now
  selects the exact nominated F record independently of the current physical
  root, then retains the original size/SHA-256 authentication. This fixes Linux
  basename parsing and an old absolute-path equality requirement without choosing
  among ambiguous same-named sources.
- Layer-3 AST fingerprints were recorded using Python 3.12. The provenance helper
  adds its absent, empty `type_params` field to copied Python-3.11 AST nodes
  before serialization. It retains existing type parameters, all semantic nodes
  and independent source-file hash checks. Five focused tests cover ambiguous
  sources, missing/duplicate records, path rejection, schema equivalence without
  mutation, and detection of semantic changes.

## Explicit runtime reference mode

`tests/audit_sampler_same_environment.py` requires an explicit authenticated
source root, exact code commit and fresh external output directory. It:

1. Uses the unchanged committed synthetic inputs, seeds and array orders.
2. Acquires only the approved original function ASTs via the existing bounded
   helpers; authenticates all required source files before evaluating references.
3. Compares original and canonical code exactly for all three Layer-1 cases,
   two Layer-2 cases and two Layer-3 cases, including recorded arrays, gradients,
   feature hashes and RNG states. A mismatch fails before suite expectations
   are replaced.
4. Supplies those independently computed original-function expectations to the
   existing test modules in memory. Original input/source metadata and every
   numerical assertion remain unchanged. Runs all 70 sampler tests and the five
   new provenance tests, with no skips permitted.
5. Saves runtime references and a report outside Git, including source identities,
   package/BLAS metadata, original fixture hashes and exact-comparison results.
   Restores module bindings and verifies committed fixture bytes are unchanged.

Ordinary unittest discovery still reads the original Windows fixtures. This
explicit audit does not claim Windows/Linux bit equality or silently overwrite
reference data. It tests the intended same-environment source/port equivalence
plus the original independent numerical and contract checks.

```bash
export PYTHONPATH="$PWD/src"
export JAX_PLATFORMS=cpu JAX_ENABLE_X64=true
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
"$cpu_environment/bin/python" -B -W error::ResourceWarning \
  tests/audit_sampler_same_environment.py \
  --source-root /work/abussing/arka_trying_gpu_again/bsfm_l4_k20_cell50_fmesher_20261026_v1/code/sampler \
  --code-commit '<exact implementation commit>' --output '<fresh external directory>'
```

Use an allocated CPU node under a committed bounded specification. This is a
continuation of CPU portability validation, not a new sampler layer, real-data
fit, mesh build or GPU test. Passing the audit does not establish those later
capabilities or solve raw-data recovery.
