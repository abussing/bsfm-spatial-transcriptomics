# User-authorized L4 execution smoke

The user requested lowering TQFF L after the L16 CPU smoke timed out. This is
an execution/return/restart check, not scientific validation of the L16 model.
Canonical L16 configuration and its strict authentication remain unchanged.

The original job 22013422 at 1aecadb completed both Layer-4 reference comparisons
and the exact chart-boundary check. It timed out after 10:04; one factor's
20-step adaptation reported acceptance [0.839, 0.893] and divergences [1, 1].
No saved genesis or completed sweep existed. A live request to extend the job
to 30 minutes was denied by Slurm. All nine external file identities and terminal
state were preserved under its output root; partial warmup is not restartable.

The retry changes L16 to L4: 32 frequency nodes, 64 cosine/sine feature columns,
fixed ell_eta=.14. Its rule comes from the same saved gamma=1.15 table, whose
complete SHA-256 matches the canonical registry's recorded table identity.
Only L4 and L16 NPY members were extracted, without executing historical code
or unpickling anything. The inspected historical tensor/pairing construction is
recorded by path/hash in L4_ell14_smoke.json and ported in build_smoke_rule.py.
An L16 reconstruction has identical weights and square-root weights; frequency
differences reach 7.105427357601002e-15. This difference is recorded rather than
claimed bitwise identity. Canonical L16 arrays are not regenerated or replaced.

L4 is authenticated by its own schema, frozen file hash and array identities.
The canonical FrozenRule boundary still rejects it. The smoke launcher explicitly
selects this rule and records its identity in the target, input binding, genesis
and checkpoints. It never relabels L4 as L16.

Two fixed shape checks in the Layer-4 joint-eta boundary now derive their column
count from the authenticated frequency array. This is the only accepted-source
file changed in the retry; numerical kernels and RNG operations are unchanged.
The earlier 181-unchanged-files receipt applies to its earlier commit, not this
new explicitly authorized dimension change. No duplicate joint-eta implementation
or runtime monkeypatch is used. Local check_rule_dimensions.py compares the
modified L16 boundary against the authenticated previous Git implementation:
eta, coefficients, diagnostics, audit and post-call RNG match exactly. It also
checks L4 draw dimensions, finite target/gradient, immutable state, rule mutation
rejection and rejection of L4 by the canonical rule boundary. The job repeats
these checks on HPC before S10 execution.

The remaining workload is unchanged: 24 cells, 91 genes, two sliced GPINIT
factors, 20 warmup steps per factor, and two total sweeps with fresh-process
resume and a completed non-replay check. The user requested avoiding another
premature wall-time kill; the cap is 30 minutes on two CPUs/8 GiB, not a target
runtime or an increase in iterations. No new mesh, SCT or GPINIT fitting occurs.

The earlier Linux-review INVENTORY.json is a frozen snapshot at 1aecadb. The
current retry files and changed boundary are covered by L4_INVENTORY.json.
No Layer-9 merge or primary holdout scoring is authorized by this smoke.
