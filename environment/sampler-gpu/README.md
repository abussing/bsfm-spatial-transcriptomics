# Candidate Linux GPU environment

This is a reproducible **wheel installation**, not a production runtime receipt.
The existing sampler authenticator still accepts only its separately validated
V100/P100 environments. Installing this candidate does not bypass that gate.

`requirements.lock` pins the complete 30-wheel closure by URL and SHA-256 for
Linux x86_64, CPython 3.11. It preserves JAX/JAXlib/CUDA plugin 0.7.0, BlackJAX 1.3,
NumPy 2.1.3, SciPy 1.14.1, JAXopt 0.8.3, Optax 0.2.8 and cuDNN 9.8.0.87 from the
existing GPU runtime. NVIDIA CUDA 12 dependencies are now explicit. Fastprogress
1.0.3 comes from the accepted Layer-5 lock; the shared GPU environment had 1.1.5
with additional web dependencies. This is a new environment requiring validation,
not a byte-identical restoration of the old one or an exact checkpoint migration.

`python-linux64.lock` supplies a SHA-256-pinned conda-forge Python **3.11.14**
base and its 25 packages. Using an existing Conda installation (the installation
check used Conda 25.7.0), create a new base outside the checkout, then create the
isolated wheel environment from a clean committed checkout:

```bash
conda create -y --prefix /external/new-python-base \
  --file environment/sampler-gpu/python-linux64.lock
bash environment/sampler-gpu/build.sh /absolute/base/bin/python \
  /external/new-environment /external/new-install-evidence
```

In that second command, `/absolute/base/bin/python` means
`/external/new-python-base/bin/python` when using the first command. Keep the
Conda installation log and the base lock hash with deployment evidence. The
host operating system, driver and GPU remain deployment inputs. The pinned base
has been installed on Linux x86_64; that installation is not a GPU execution test.

The script refuses existing destinations, installs only authenticated wheels,
checks dependencies and package isolation, and writes logs, installation reports,
interpreter/RECORD hashes and the source commit outside Git. It does not import JAX,
run numerical work, request a GPU or submit a job. Do not use the installation
receipt as an argument to the production runtime authenticator.

For device validation, freeze an external job specification and obtain the
required job authorization. On one allocated GPU, using the candidate Python:

```bash
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
python -I environment/sampler-gpu/validate.py --commit FULL_COMMIT_SHA \
  --installation /external/new-install-evidence/installation.json \
  --installation-sha256 RECEIPT_SHA256 --output /external/new-validation-output
```

This checks interpreter/package payload integrity, one GPU and float64, the GPU
callback, independent dense target/gradient oracles, and existing synthetic
deep/flat controller, prediction and restart tests. `validation.json` and
`tests.log` are external; retain scheduler stdout/stderr too. Tests reuse canonical
transitions; test-only contracts do not authenticate a production CLI runtime.
A passing report therefore **does not admit production** or prove scientific
mixing. The new-device admission interface and actual-CLI validation remain
outstanding. Keep CUDA-13 modules and unrelated library search paths out of a
CUDA-12 candidate's validation process. The installer itself does not alter modules.
