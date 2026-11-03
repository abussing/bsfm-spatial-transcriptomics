# Available P100 paired fallback

**Superseded job map:** deep job 22014562 failed on a logging callback and was
replaced by 22014615; flat 22014563 was preserved. Use
[CURRENT_GPU_JOBS.md](CURRENT_GPU_JOBS.md) for current commits, outputs and resume.

To obtain a paired result while V100 queues remain congested, the same
`circles12_diameter1of8` deep/flat fits were additionally submitted on `gpu`:

| Model | Job |
| --- | --- |
| Deep | 22014562 |
| Flat | 22014563 |

Generating commit: `bca5878664eb7687a127f05323e5b9032440eb27`.
One Tesla P100-PCIE-16GB per job, four CPUs, 16 GiB host memory, 12 hours.
Same K12, L14, full mesh, inputs, seed and tune50/bridge50/retune100/production1000.
Existing V100 16GB and 32GB submissions were not moved or cancelled.

Output root:
`/work/abussing/bsfm-consolidation/evidence/holey-gpu-bca5878664eb7687a127f05323e5b9032440eb27-p100`.
Logs: `/work/abussing/bsfm-consolidation/evidence/holey-gpu-JOBID.log`.
Check current Slurm/log state; this document records submission, not completion.

P100 validation job 22014518 completed 0:0 in 4:42. Four focused synthetic tests
passed, including both models' phase transitions and resume/nonreplay. A real
L14 first-factor 20-step warmup took 128.41 seconds including compilation.
This validates bounded execution, not complete 50/100-step full-input adaptation
or scientific convergence. See `P100_VALIDATION_RECEIPT.json` and its external
log/timing hashes. The existing GPU environment was reused unchanged.

```sh
sbatch --partition=gpu docs/holdouts/s10-grid-20261103/gpu_sample.sbatch \
  bca5878664eb7687a127f05323e5b9032440eb27 circles12_diameter1of8 deep p100
```

Resume only after the old writer exits and with the same runtime/device identity.
The generic queue is preemptible. Initial warmup is not checkpointed stepwise.
These are queue alternatives, not extra independent chains; never pool duplicate
same-seed fits as independent evidence. Do not write into V100 or CPU directories.
