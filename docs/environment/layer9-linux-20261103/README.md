# Linux sampler environment build

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
