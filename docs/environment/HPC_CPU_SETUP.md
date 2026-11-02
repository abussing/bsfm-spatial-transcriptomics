# HPC CPU portability setup

2026-11-02. Status: **installed, dependency and CPU/x64 import checks passed;
canonical sampler numerical tests pending**. This is not GPU validation or a
production sampler environment. No scheduler job was submitted during setup.

Host: `abussing@login.rci.sc.edu`, SSH port 222, observed node `login001`.
New environment: `/work/abussing/bsfm-consolidation/environments/sampler-cpu-py311`.
Its `bin/python` is the execution entry point. Existing historical environments
were not modified. The new venv shares the existing base Python runtime at
`/work/abussing/arka_trying_gpu_again/env`; it is not a self-contained runtime
backup and that base must remain available.

## Versions and installation

CPython 3.11.14 (conda-forge), Linux x86-64/glibc 2.17. This uses the historical
Python version, differing from the accepted Windows 3.12.0 validation machine.
All seven numerical/helper pins from Layer 2 are unchanged: JAX/JAXlib 0.7.0,
NumPy 2.1.3, SciPy 1.14.1, ml_dtypes 0.6.0, opt_einsum 3.4.0,
threadpoolctl 3.5.0. Bootstrap packages are pip 24.0 and setuptools 79.0.1.

Measured base Python executable SHA-256:
`9b3ba347a7b9dc429404683fd24fad63d96826be1817482541f905a1fac06cd7`.
Compiler reports conda-forge GCC 15.2.0-7. Measured driver hashes:
gcc `6af311d4ce51974b5d88bee9bc10de39bd63d3c13c689bf7aca5818e176ff69c`;
c++ `0ef67c4fbc1d663ff298e71b4c03e23e42fa3839e3aab80ef20888c515e7c90c`.
These are partial toolchain identities, not a complete sysroot lock.

The initial binary-only resolver rejected ml_dtypes 0.6.0: its official
CPython-3.11 Linux wheel needs glibc 2.27+, while this host has glibc 2.17.
The same version was successfully built from the official PyPI source archive,
using the existing conda C/C++ compiler and one build thread. Source identity:

- URL: `https://files.pythonhosted.org/packages/12/72/307d7c4bd0600601c7133fba5cb78af7db968152951c1cd473abb1cda782/ml_dtypes-0.6.0.tar.gz`
- PyPI-recorded size: 3,032,327 bytes.
- PyPI-recorded SHA-256: `5e602511d32ced5598972e4d5e06a2f044341f9291402551a3f6f0ec44f9299b0`.
- Produced wheel: `ml_dtypes-0.6.0-cp311-cp311-linux_x86_64.whl`, 415,898 bytes.
- Measured wheel SHA-256: `61c6ecb5f6baac2c1e602305dd57be2ab9d494f02dcd11c9dc82150f0421de10`.

Six other wheels were downloaded from official PyPI with exact versions.
All seven wheel hashes were frozen before offline installation with
`--no-index --no-deps --require-hashes`. The
[Linux installation lock](../../environment/sampler-linux-cpu/requirements.lock.txt)
is distinct from the unchanged Windows lock. Wheels remain under the new
environment's `wheels/` directory, and `installed.json` records packages,
wheel hashes, base runtime, CPU backend and x64.

Installation commands, with `base` and `root` set to the paths above:

```bash
"$base/bin/python3" -I -m venv "$root"
CC="$base/bin/x86_64-conda-linux-gnu-gcc" \
CXX="$base/bin/x86_64-conda-linux-gnu-c++" CMAKE_BUILD_PARALLEL_LEVEL=1 \
"$root/bin/python" -I -m pip --isolated wheel --no-deps \
  --no-binary=ml_dtypes --index-url https://pypi.org/simple \
  --wheel-dir "$root/wheels" ml_dtypes==0.6.0
"$root/bin/python" -I -m pip --isolated download --only-binary=:all: --no-deps \
  --index-url https://pypi.org/simple --dest "$root/wheels" \
  jax==0.7.0 jaxlib==0.7.0 numpy==2.1.3 scipy==1.14.1 \
  opt_einsum==3.4.0 threadpoolctl==3.5.0
"$root/bin/python" -I -m pip --isolated install --no-index --no-deps \
  --require-hashes --find-links "$root/wheels" \
  -r environment/sampler-linux-cpu/requirements.lock.txt
"$root/bin/python" -I -m pip check
```

For the actual initial installation, the identical requirements file was generated
from measured wheel hashes under `$root/requirements-linux.lock.txt`; the repo
copy records those hashes. Setup logs are external under
`/work/abussing/bsfm-consolidation/evidence/`:
`ml-dtypes-build.log`, `sampler-download.log`, `sampler-install.log`.

## Evidence limits and next validation

`pip check` reports no broken requirements. Imports of JAX, NumPy, SciPy and
ml_dtypes succeeded with `JAX_PLATFORMS=cpu`, `JAX_ENABLE_X64=true`,
`OMP_NUM_THREADS=1`, `OPENBLAS_NUM_THREADS=1`; JAX reports CPU and x64 enabled.
No canonical test suite or scientific fit has been executed on this environment.

The retained wheel lock supports offline package restoration on a compatible
Python/Linux runtime. The initial isolated source build resolved build tools
dynamically; a complete compiler/sysroot/build-dependency lock and independent
rebuild have not been established. Thus this is not a claim of byte-reproducible
source builds. Preserve the authenticated wheel and base runtime until that
additional restoration work is completed.

Next: run the 70 committed sampler tests on an allocated CPU node against
`49f33c441e1cde9e1b8139ffef0103993eaa0222`, using the saved synthetic fixtures.
Record all failures and platform differences without weakening thresholds or
rewriting fixtures. Mesh/R tests, full-cell S10 smoke, real-data fits and GPU
validation are separate gates with additional inputs. A committed run
specification and explicit approval are required before scheduler submission.
The prepared [run specification](HPC_CPU_VALIDATION_RUN.json) requests one CPU,
8 GiB and at most 15 minutes on defq-64core; it has not been submitted.
