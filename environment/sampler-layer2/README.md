# Sampler layer-2 CPU development environment

Status: built and validated; accepted CPU development environment for sampler
Layer 2. This is not a CUDA/GPU production environment or a complete sampler
dependency lock.

Machine-local isolated root:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer2-cpu-20261102`.
Executable: `python/Scripts/python.exe` beneath that root.

| Component | Version |
| --- | --- |
| CPython | 3.12.0, Windows x86-64 |
| JAX / JAXlib | 0.7.0 / 0.7.0, CPU |
| NumPy / SciPy | 2.1.3 / 1.14.1 |
| ml_dtypes / opt_einsum | 0.6.0 / 3.4.0 |
| threadpoolctl | 3.5.0 |
| pip bootstrap | 23.2.1 |

Python 3.11.14 was preferred where feasible. The bounded registered-runtime
query (`py -0p`) found the already authenticated Python 3.12.0, plus unrelated
older runtimes, and no 3.11 runtime. The official
[3.11.14 release](https://www.python.org/downloads/release/python-31114/)
provides no Windows binary installer. This build reuses the existing immutable
`C:\Program Files\Python312\python.exe` and recorded DLL identities instead of
reconstructing another runtime. This is an explicit development-platform
difference, not a historical Python/Linux reproduction claim.
[JAXlib 0.7.0](https://pypi.org/project/jaxlib/0.7.0/) provides a CPython 3.12
Windows wheel and declares Python >=3.11. The resolved wheel metadata and
successful installation/import tests establish compatibility for this build.

[source-lock.json](source-lock.json) records every resolved wheel URL and SHA-256,
runtime identities and package constraints. [build-validation.json](build-validation.json)
records downloaded sizes/hashes, actual installation command, complete installed
package set, x64 CPU backend, library isolation, architecture and BLAS metadata.
[freeze.txt](freeze.txt) includes bootstrap pip. The two transitive package
versions are resolved local pins, not recovered historical session versions.
All numerical validation used one BLAS thread and JAX x64 on CPU. This is a
bounded test setting, not a production thread/resource policy.

Actual acquisition began with a fresh venv and this resolver command (the root
below abbreviates the full machine-local path above):

```text
"C:\Program Files\Python312\python.exe" -I -m venv <root>/python
<root>/python/Scripts/python.exe -I -m pip --isolated install --dry-run --ignore-installed --only-binary=:all: --no-cache-dir --index-url https://pypi.org/simple --report <root>/resolution.json jax==0.7.0 jaxlib==0.7.0 numpy==2.1.3 scipy==1.14.1 threadpoolctl==3.5.0
```

The large resolver record stays outside Git. No packages were installed by that
dry run. Its resolved package identities were frozen before installation.

Reproduction from the frozen lock, with an explicitly approved fresh destination:

```powershell
& 'C:\Program Files\Python312\python.exe' -B environment/sampler-layer2/build.py `
  --root '<fresh external root>' --acquire
```

The [builder](build.py) downloads only the seven exact recorded official PyPI
wheels, checks SHA-256, then installs with `--no-index --no-deps --require-hashes`
using [requirements.lock.txt](requirements.lock.txt). It rejects an already
installed or nonempty package environment. Omitting `--acquire` requires the
authenticated wheels already present under the fresh root's `wheels/` directory.
There is no runtime dependency substitution or new resolution in this builder.
The build was performed once; a second independent restoration was not run.

Existing SCTransform, mesh, GPINIT, system and user libraries were not installation
targets. The three shared runtime executable/DLL hashes still match. The new venv
has no system site packages and disables user site packages; its recorded search
path contains no unrelated package library. Archives and installed binaries remain
outside Git. No GPU packages, BlackJAX, HPC work or full sampler execution occurred.

The only diagnostic warning was NumPy's optional PyYAML suggestion during
`show_config()`. Plain-text build metadata was retained; PyYAML was not installed.
No warning was suppressed. Early acquisition setup hit a Windows text-decoding
error before writing the lock; specifying UTF-8 fixed the metadata read before
installation. This did not change package choices.

See the [layer-2 report](../../docs/sampler/LAYER2.md) for mathematical tests,
same-environment historical comparisons and their limits.
