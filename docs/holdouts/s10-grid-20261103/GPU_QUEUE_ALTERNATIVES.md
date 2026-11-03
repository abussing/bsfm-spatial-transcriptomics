# Additional V100 32GB submissions

Use [CURRENT_GPU_JOBS.md](CURRENT_GPU_JOBS.md) for current job IDs and generating
commits after the deep-only callback retry. The table below is earlier launch evidence.

The idle generic queue was identified as P100 and passed bounded execution
validation. [A paired P100 fallback](P100_RUNNING.md) was additionally submitted;
the V100 submissions below remain in place.

The user explicitly requested additional submissions rather than moving the
original eight pending V100 16GB jobs. The existing jobs 22014441-22014448 remain
in place at generating commit `18e437fc7960860f093bc0a79481fff356b4e1e9`.

Additional generating commit: `c6f23ad2c9d03fc6421f878b20e0d8a107cbaa2e`.
Partition: `v100-32gb-hiprio`; submission tag: `v10032`.
Same eight fits, numerical source, inputs, K=12, L14 and iteration schedule.
One GPU, four CPUs, 16 GiB host memory and 12 hours per job.

| Configuration | Deep | Flat |
| --- | --- | --- |
| circles12_diameter1of8 | 22014499 | 22014500 |
| circles12_diameter1of16 | 22014501 | 22014502 |
| circles8_diameter1of16 | 22014503 | 22014504 |
| circles8_diameter1of8 | 22014505 | 22014506 |

Separate output root:
`/work/abussing/bsfm-consolidation/evidence/holey-gpu-c6f23ad2c9d03fc6421f878b20e0d8a107cbaa2e-v10032`.
Never combine duplicate same-seed queue alternatives as independent chains.
They never share checkpoint directories. Check current job states before
deciding which duplicate attempts to keep; no original job was moved or cancelled.

Exact submission command from the generating checkout:

```sh
sbatch --partition=v100-32gb-hiprio \
  docs/holdouts/s10-grid-20261103/gpu_sample.sbatch \
  c6f23ad2c9d03fc6421f878b20e0d8a107cbaa2e circles12_diameter1of8 deep v10032
```

Other inspected queues: `gpu-v100-32gb` and `gpu-v100-16gb` overlap the high
priority pools, each with three additional nodes, and use preemptible/requeue
policy. `minsky` is down. The generic `gpu` partition showed idle node242 but no
model/driver identity; hardware-only job 22014507 requests one GPU for at most
five minutes and reports hostname/nvidia-smi. It performs no scientific work.
Read its log `/work/abussing/bsfm-consolidation/evidence/gpu-inventory-22014507.log`
before treating that older node as compatible.
