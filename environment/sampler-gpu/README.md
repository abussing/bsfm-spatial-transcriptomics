# Candidate Linux GPU environment

This provides a pinned wheel installation, numerical validation, and an explicit
runtime interface for the normal sampler launcher. Installation alone does not
authorize GPU execution. Existing V100/P100 recipes retain their original
authenticator and checkpoint identities.

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

Installation disables pip bytecode compilation, and validation disables Python
cache writes. Some wheels contain a hashed bytecode file that pip would otherwise
overwrite while retaining its old RECORD digest. The verifier still authenticates
every hashed payload, including those caches; it does not ignore mismatches.
Before requesting a GPU, run the validation command below with the additional
`--installation-only` flag and a separate output directory. That mode checks all
installed payloads without importing JAX or running numerical work.

For device validation, freeze an external job specification and obtain the
required job authorization. On one allocated GPU, using the candidate Python:

```bash
export PYTHONNOUSERSITE=1 PYTHONDONTWRITEBYTECODE=1
python -I -B environment/sampler-gpu/validate.py --commit FULL_COMMIT_SHA \
  --installation /external/new-install-evidence/installation.json \
  --installation-sha256 RECEIPT_SHA256 --output /external/new-validation-output
```

This checks interpreter/package payload integrity, one GPU and float64, the GPU
callback, independent dense target/gradient oracles, and existing synthetic
deep/flat controller, prediction and restart tests. `validation.json` and
`tests.log` are external; retain scheduler stdout/stderr too. Tests reuse canonical
transitions; test-only contracts do not authenticate a production CLI runtime.
A passing report does not prove scientific mixing or completion of the normal
command workflow. Keep CUDA-13 modules and unrelated library search paths out of a
CUDA-12 candidate's validation process. The installer itself does not alter modules.

## Connect the validated runtime to the sampler

After numerical validation passes, use this explicit `gpu_runtime` object in an
external sampler recipe (paths resolve relative to that recipe):

```json
{
  "schema": "bsfm.validated-gpu-runtime.v1",
  "installation": "/external/install/installation.json",
  "installation_sha256": "INSTALLATION_SHA256",
  "validation": "/external/numerical-check/validation.json",
  "validation_sha256": "NUMERICAL_RECEIPT_SHA256",
  "validation_plan": "/external/numerical-plan/run-spec.json",
  "validation_plan_sha256": "FROZEN_PLAN_SHA256",
  "libdevice": "/external/environment/lib/python3.11/site-packages/nvidia/cuda_nvcc/nvvm/libdevice/libdevice.10.bc",
  "blas_threads": 1
}
```

The authenticator requires all 12 checks in the v1 numerical validator to pass
without skips, matching installation/plan identities and the exact tested GPU
model. It rechecks the interpreter, wheel lock, package payloads, libdevice,
float64, GPU backend and one BLAS thread. The pinned receipts are explicit trust
inputs; retain the corresponding job logs and verify their origin. New-runtime
identities differ from legacy identities: this is not cross-runtime exact resume.

Before scientific fitting, test the actual launcher using two tiny frozen
synthetic recipes, deep and **learned-range** flat. Reuse the existing
[synthetic fixture inventory](../../docs/environment/shared-run-gpu-20261105/FIXTURE_INVENTORY.json)
or regenerate that fixture with its named test producer; regenerated hashes must
be frozen explicitly. Put both recipe records (`path`, `bytes`, `sha256`) under
`recipes: {"deep": ..., "flat": ...}` in an external manifest with schema
`bsfm.cli-validation-inputs.v1`. Freeze that manifest and all runtime/input hashes
in the separately authorized job plan. With the deployment variables from the
workflow guide set, run on one allocated GPU:

```bash
python -I -B environment/sampler-gpu/validate_cli.py --commit FULL_COMMIT_SHA \
  --recipes /external/cli-recipes.json --recipes-sha256 MANIFEST_SHA256 \
  --output /external/new-cli-validation
```

This invokes a spooled copy of `environment/hpc/sample.sbatch`, verifies phase and
save counts, and reruns each completed command to check that neither tuning nor
sweeps replay and the complete saved-file inventory stays unchanged. Logs and
`validation.json` remain external. Passing numerical and CLI checks establishes
bounded execution on that runtime, not scientific mixing or general numerical
robustness for every dataset.
