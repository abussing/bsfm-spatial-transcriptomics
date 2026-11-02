# Isolated C3 GP-initialization environment

This local environment was installed with explicit user approval and accepted
for the bounded canonical cold-start capability. It does not
modify Anaconda, the accepted SCTransform environment, or the mesh environment.

Machine-local root:
`C:\Users\Data Viz\Desktop\Anderson_Hail\BSFM_ENVIRONMENTS\gpinit-20261102`.
The immutable existing `C:\Program Files\Python312\python.exe` creates the venv.
Its executable and DLL identities still match the accepted mesh runtime lock.

The [source lock](source-lock.json) records actual installed wheel URLs and
SHA-256 values. [Requirements](requirements.lock.txt) pin every runtime package
used by this initializer: NumPy 2.1.3, SciPy 1.14.1, scikit-learn 1.4.2,
joblib 1.4.2, threadpoolctl 3.5.0. The first three match the historical package's
`code/requirements-core.txt`; the last two are explicit local transitive pins,
not recovered historical session measurements. Pip 23.2.1 comes from the
existing runtime's venv bootstrap.

For a fresh, separately approved destination, create a venv using the recorded
base executable and install using its Python with:

```text
python -I -m pip --isolated install --only-binary=:all: --require-hashes --no-deps --index-url https://pypi.org/simple -r environment/gpinit/requirements.lock.txt
```

Use `PYTHONPATH=<repository>/src`, then run the bounded tests with that venv's
Python: `python -B -m unittest discover -s tests -p test_gp_initialization.py -v`.
The configuration limits numerical libraries to four threads, matching the
historical preparation wrapper. No installation or environment rebuilding
happens automatically when calling the initializer.

This is Windows Python 3.12.0. The historical package records Linux Python
3.11.14; that package record is not a session attestation of S10's GPINIT fit.
The cross-platform S10 comparison is accepted as cold-start equivalent under the
[explicit historical regression policy](../../config/initialization/historical-regression.json),
not exact. No platform
substitution is claimed to reproduce identical optimized GP parameters or SVD
bits. The known Anaconda native-import failure is not retried or repaired here.
Only GP-initialization runtime dependencies are installed; this is not a claim
that this venv contains every other capability's test dependencies.
