# Linux sampler environment build

Job 22013403 at commit ecfbde4 failed in 13 seconds before installation:
the selected ml_dtypes 0.6.0 wheel requires glibc 2.27, while HPC has 2.17.
Its exact submission receipt, build report and log are preserved here; its
external prefix remains intact. This was a platform-selection error, not a
sampler test failure. No scientific data was processed.

The correction keeps all 13 runtime package versions unchanged and compiles
ml_dtypes 0.6.0 from its hash-locked official PyPI source distribution using
existing HPC GCC 12.2, CMake 3.27.4 and Ninja 1.10.2 modules. Build packages are
installed in a separate build environment, never the sampler environment.
The source build uses the accepted NumPy 2.1.3, satisfying upstream `numpy~=2.0`.
The generated wheel receives its own hash and is retained with the report.

RUN_SPEC.json retains the approved environment-only limits: 2 CPUs, 8 GiB,
30 minutes, fresh isolated prefix. Both build attempts and any numerical
validation must be reported separately. Environment success does not accept
Layer 9 or validate scientific outputs.

Upstream references: [source metadata](https://pypi.org/pypi/ml_dtypes/0.6.0/json),
[build requirements](https://github.com/jax-ml/ml_dtypes/blob/v0.6.0/pyproject.toml),
[compiler requirements](https://github.com/jax-ml/ml_dtypes/blob/v0.6.0/CMakeLists.txt).
