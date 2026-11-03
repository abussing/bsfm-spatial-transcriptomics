# Linux sampler environment build

## Completed environment restoration

Job **22013408** completed with exit 0:0 in 00:01:14; batch MaxRSS 803116K.
Generating commit: `460ccdd6ca523d22f2c61c0cbacdf0f1f82ba0de`.
All 13 runtime package versions match the accepted version list; pip check,
CPU/x64 and module-path isolation passed. Build-only packages are absent from
the runtime venv. Bootstrap packages are recorded separately: pip 24.0 and
setuptools 79.0.1. This is a Linux Python 3.11.14 environment, not the accepted
Windows Python 3.12.0 runtime or a claim of cross-platform exact numerical output.

```text
/work/abussing/bsfm-consolidation/environments/sampler-layer9-cpu-20261103-source4/python/bin/python
```

The build used `module load gcc/12.2.0 mpfr/4.1.0`; preserve that module context
for the next validation until runtime shared-library requirements are explicitly
checked. Launch numerical work only through an approved scheduler specification.
The exact package report, build report, logs, submission and scheduler accounting
are retained here as `job22013408-*`; full caches, built wheel and installation
remain under the external prefix. The report authenticates the source archives,
built wheel, compiler paths and package report. Earlier failed prefixes remain.

No sampler tests, scientific fits, mesh regeneration or preprocessing were run
by these environment jobs. Next requirements remain Linux writer/runtime
authentication support and synthetic sampler initialization/sweep/resume checks.

## Preserved failure history and corrections

Job 22013403 at commit ecfbde4 failed in 13 seconds before installation:
the selected ml_dtypes 0.6.0 wheel requires glibc 2.27, while HPC has 2.17.
Its exact submission receipt, build report and log are preserved here; its
external prefix remains intact. This was a platform-selection error, not a
sampler test failure. No scientific data was processed.

The correction keeps all 13 runtime package versions unchanged and compiles
ml_dtypes 0.6.0 from its hash-locked official PyPI source distribution using
existing HPC GCC 12.2 and hash-locked portable CMake/Ninja wheels. Build packages are
installed in a separate build environment, never the sampler environment.
The source build uses the accepted NumPy 2.1.3, satisfying upstream `numpy~=2.0`.
The generated wheel receives its own hash and is retained with the report.

RUN_SPEC.json retains the approved environment-only limits: 2 CPUs, 8 GiB,
30 minutes, fresh isolated prefix. Both build attempts and any numerical
validation must be reported separately. Environment success does not accept
Layer 9 or validate scientific outputs.

Job 22013404 at bc5bee6 failed in two seconds before downloads or compilation:
the system CMake module works on the login host but requires an unavailable
OpenSSL symbol on the compute node. The next prefix is `source2`; `source1`
remains preserved. Portable CMake 3.27.9 and Ninja 1.11.1.1 wheels now reside
only in the build venv. No OS library, runtime package version or scientific
code is changed by this correction.

Job 22013405 at deaaf83 reached source configuration but GCC's cc1plus could
not load libmpfr.so.6. The GCC module does not load that dependency itself.
The next attempt explicitly loads the existing mpfr/4.1.0 module; read-only
loader inspection confirms all cc1plus libraries resolve with that module.
Its fresh prefix is `source3`; the successful authenticated downloads from
`source2` are reused only after rehashing. Module/library paths are recorded.

Job 22013406 at b09e079 compiled the source, but the strict wheel-version check
rejected its 0.0.0 metadata before runtime installation. The source's
`[[tool.dynamic-metadata]]` format requires scikit-build-core >=1.0, unlike the
initially pinned 0.11.6. The corrected build backend is pinned to 1.1.2 in its
separate build venv. No source patch or wheel relabeling is used. The next fresh
prefix is `source4`, and pip's shared cache is disabled.
See [upstream metadata-format documentation](https://scikit-build-core.readthedocs.io/en/latest/configuration/dynamic.html).

Upstream references: [source metadata](https://pypi.org/pypi/ml_dtypes/0.6.0/json),
[build requirements](https://github.com/jax-ml/ml_dtypes/blob/v0.6.0/pyproject.toml),
[compiler requirements](https://github.com/jax-ml/ml_dtypes/blob/v0.6.0/CMakeLists.txt).
