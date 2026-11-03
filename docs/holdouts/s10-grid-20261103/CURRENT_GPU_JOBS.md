# Current GPU job map

This supersedes job IDs and generating-commit assumptions in earlier launch
records. It records the callback correction after P100 deep job 22014562 failed.
Check Slurm/logs for live state; running does not imply completion or convergence.

## P100 pair: 12 holes, diameter width/8

| Model | Job | Generating commit | Output tag |
| --- | --- | --- | --- |
| Deep | 22014615 | 73939be3fd8cb37dfb96022d656ce999b48d8eaa | p100 |
| Flat | 22014563 | bca5878664eb7687a127f05323e5b9032440eb27 | p100 |

Both were RUNNING on node242 at the last check. Deep passed the forced rare
callback preflight on cuda:0 and entered initial tuning. Flat had completed all
12 initial warmups and saved five bridge sweeps. No production result is claimed.
Old deep job 22014562 failed before genesis; its outputs remain preserved.

## V100 alternatives

| Configuration | 16GB deep | 16GB flat | 32GB deep | 32GB flat |
| --- | --- | --- | --- | --- |
| circles12_diameter1of8 | 22014622 | 22014442 | 22014623 | 22014500 |
| circles12_diameter1of16 | 22014624 | 22014444 | 22014625 | 22014502 |
| circles8_diameter1of16 | 22014626 | 22014446 | 22014627 | 22014504 |
| circles8_diameter1of8 | 22014628 | 22014448 | 22014629 | 22014506 |

Deep generating commit in both queues: `73939be3fd8cb37dfb96022d656ce999b48d8eaa`.
16GB flat commit: `18e437fc7960860f093bc0a79481fff356b4e1e9`, tag `primary`.
32GB flat commit: `c6f23ad2c9d03fc6421f878b20e0d8a107cbaa2e`, tag `v10032`.
Deep tags are `primary` (16GB) and `v10032` (32GB). Only the eight affected
pending deep jobs were cancelled/replaced; all flat submissions were preserved.
16GB jobs exclude node398 after its pre-application failures.

## Monitoring and resumption

Logs: `/work/abussing/bsfm-consolidation/evidence/holey-gpu-JOBID.log`.
Output roots: `/work/abussing/bsfm-consolidation/evidence/holey-gpu-COMMIT-TAG`,
except `primary`, which omits the `-TAG` suffix. Within each root:
`CONFIGURATION/MODEL/{bridge,production}/segments/segment/transactions/`.
Each committed `record.npz` is one saved sweep. Bridge draws are excluded from
production predictions. Deep and flat outputs now reside under different commits;
select their snapshots explicitly for the comparison renderer.

Resume from the exact clean generating checkout, after confirming the previous
writer exited, using `gpu_sample.sbatch COMMIT CONFIGURATION MODEL TAG` and the
matching `--partition` override. Same-seed queue alternatives are not independent
chains and must not be pooled as such. Preserve CPU and failed-run evidence.

## Callback correction

The GPU-only platform list hid the CPU device needed by `jax.debug.print`.
The corrected launchers expose `JAX_PLATFORMS=cuda,cpu`; CUDA remains the default
computation backend and the runner rejects CPU computation. A forced one-ULP
acceptance overshoot now tests the callback before initialization, verifies the
result lives on GPU, and waits for callback completion. Job 22014615 passed it.
No scientific parameters, kernels, inputs, RNG chronology or iteration counts
changed in this launcher correction. The working flat path uses no such callback
and was left untouched.

All fits retain K12, L14, the full mesh, 91 genes/3 types, target_accept0.9,
50 initial tuning steps per factor, 50 bridge sweeps, 100 retuning steps per
factor and 1000 production sweeps. One GPU, four CPUs, 16 GiB host memory,
12 hours per job. Save/checkpoint each complete sweep.
