# Current execution branch

The requested K12/L14 paired runs are now preserved on
`run/s10-holey-20261103`; generating commit
`27f9b3f0dfa4c1df2acc9e845633a8031069daea`.
Read that branch's `RUNNING.md` and `RUNNING_RECEIPT.json` in this directory.
The source-only branch carries the tested sampler code from review commit
44c9955 without requiring transfer of this branch's large plot history.
Preparation-only corrections there retain crash traces, bind the existing GP
dependency prefix and use one BLAS thread to avoid the observed Linux SciPy
Cholesky segfault. All four preparations then passed, and all eight deep/flat
jobs were observed running. Check current Slurm status before making a new claim.

Main's CURRENT_HANDOFF.md points to that execution checkpoint. No scientific
code was merged into main. Do not relaunch the superseded initial submissions.
