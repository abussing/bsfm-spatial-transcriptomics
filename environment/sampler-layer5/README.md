# Layer-5 CPU environment — review proposal

Separate Windows CPU development environment for the
[split transition/adaptation proposal](../../docs/sampler/LAYER5.md).
It does not modify the accepted Layer-2 environment and does not establish
CUDA/GPU/HPC readiness or a complete sampler environment.

Machine-local build root:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-cpu-20261102`.
The immutable existing Python 3.12.0 runtime under `C:\Program Files\Python312`
is reused, with its three recorded file hashes verified. No global installation
or user site is used. Python 3.11.14 remains a historical-platform difference,
already recorded for Layer 2; no new runtime archaeology was performed.

| Package | Frozen version |
| --- | --- |
| Python / pip | 3.12.0 / 23.2.1 |
| JAX / JAXlib | 0.7.0 / 0.7.0 |
| NumPy / SciPy | 2.1.3 / 1.14.1 |
| ml_dtypes / opt_einsum / threadpoolctl | 0.6.0 / 3.4.0 / 3.5.0 |
| BlackJAX | 1.3 |
| jaxopt / optax | 0.8.3 / 0.2.8 |
| fastprogress | 1.0.3 |
| absl-py / typing_extensions | 2.5.1 / 4.16.0 |

The resolver retained every accepted Layer-2 pin. `fastprogress==1.0.3` satisfies
BlackJAX's dependency constraint without the unrelated web-application closure
introduced by newer fastprogress. This is a dependency selection, not a change
to the sampler. All packages resolved together and `pip check` passed.
The [official BlackJAX 1.3 release metadata](https://pypi.org/pypi/blackjax/1.3/json)
defines its requirements; the exact installed wheel source, rather than newer
online API documentation, defines the adaptation implementation tested here.

Records:

- [source-lock.json](source-lock.json): exact official PyPI wheel URLs, SHA-256,
  versions, constraints and runtime identities.
- [requirements.lock.txt](requirements.lock.txt): complete hashed installation.
- [base-constraints.txt](base-constraints.txt): resolution inputs.
- [freeze.txt](freeze.txt): complete installed package set including pip.
- [build-validation.json](build-validation.json): sizes/hashes, installation
  commands, exact runtime, package isolation, CPU/x64 and BLAS metadata.
- [restore-validation.json](restore-validation.json): independently installed
  offline restoration environment and authenticated package records.
- [restoration-comparison.json](restoration-comparison.json): exact semantic
  restoration and the unchanged 6,055-file accepted Layer-2 inventory.

The initial Windows installation/restoration read CRLF lock files. The proposal
normalizes repository text to LF as required by `.gitattributes`. Original
installation hashes remain recorded; validation authenticates the exact
LF-to-CRLF byte conversion and records both identities. Package/version/wheel
content is unchanged; arbitrary whitespace or semantic substitutions are not
accepted. New restorations read the canonical LF locks directly.

## Build and offline restoration

[build.py](build.py) validates runtime identities first. Downloads occur only
with `--acquire`; installation always uses `--no-index --no-deps --require-hashes`
and the complete lock. It refuses a populated library or existing installed
receipt. Never point it at an accepted environment. No version substitution or
network dependency resolution is performed during installation/restoration.

```powershell
& 'C:\Program Files\Python312\python.exe' -B environment/sampler-layer5/build.py `
  --root 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-cpu-20261102' --acquire

& 'C:\Program Files\Python312\python.exe' -B environment/sampler-layer5/build.py `
  --root 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-restore-check-20261102' `
  --wheel-cache 'C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\sampler-layer5-cpu-20261102\wheels'
```

The restoration uses a fresh venv and authenticated cached wheels, not copied
installed libraries. The restoration root is retained outside Git for review.
Validate either environment with its own interpreter using `-I -B`, the CPU/x64
and single-thread environment settings in the Layer-5 report, and
`environment/sampler-layer5/validate.py --output <receipt.json>`.
Installed directories need not be byte-identical across roots. Runtime, package,
archive, BLAS and semantic checks carry the reproducibility claim.
