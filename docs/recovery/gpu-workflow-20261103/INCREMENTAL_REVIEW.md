# Proposed validation-lifetime amendment

Status: **review candidate, not selected by any launcher**. Source is `src/bsfm/sampler/run_incremental.py`; existing `Transactions`, `RunController`, public Layer-7/8 readers and numerical kernels are unchanged. Tests select the candidate explicitly. No active HPC checkout or fit is edited.

## Historical practice and canonical correction

The authenticated historical driver retains the live state, advances one sweep, writes its current checkpoint and retained state, and continues. It does not numerically reconstruct every prior state before taking the next step. Canonical atomic checkpoint+record publication and genesis/restart rules are intentional improvements over that driver and are retained.

Layer-9A section 6 step 9 currently specifies a complete archive reopen and resume check after each commit. This proposal changes that *validation lifetime* during uninterrupted exclusive ownership. It does not claim the old wording already allowed a cached strict archive, nor does it replace the independent new-pair validation with a cached hash.

## Proposed behavior

- At entry under a new writer lease, perform the existing complete transaction scan and complete projection/archive validation. Read-only scans outside a lease always use the original strict path.
- Cache only the validated chain endpoint, receipts and file metadata for that exact lease. Lease identity is the actual ContextVar tuple object; releasing and reacquiring the same root in the same process invalidates the cache.
- Before each advance, inspect the existing transaction namespace and metadata of previously validated transaction files/directories, genesis, immutable run/input specs, and derived projections. Ordinary deletion, replacement, resizing or timestamp changes fail closed.
- After a new directory is published, reopen it with the original independent checkpoint and record readers through `Transactions.pair`. Require the exact next index and predecessor, RNG/state boundary, contract and frozen tuning. Advance the in-memory endpoint only after this passes.
- Copy only the new projections, verify their bytes against the independently validated transaction, and update the advisory ledger. An incremental projection result is `None`, deliberately not a forged `RetainedArchive` claiming full revalidation.
- At final closure, repeat a complete transaction scan and the original strict archive validation/diagnostic aggregation. Recovery after interruption always starts with full validation and the existing prepared-pair rules.

The expensive numerical validation work per ordinary sweep becomes independent of the number of old records. Metadata/namespace checking still scales with history length; this proposal does not falsely claim O(1) filesystem work or promise a GPU speedup before measurement. Full validation at resume/closure remains linear in history size.

## Integrity scope

This depends on the existing cooperating single-writer, immutable-publication assumptions. Metadata guards are **not** cryptographic detection of an external actor that spoofs file metadata, nor of silent corruption preserving metadata. Full resume/closure checks still authenticate file contents. No partial-corruption scenario is converted into stochastic replay. The review must explicitly accept this validation-lifetime tradeoff rather than remove guards without saying so.

## Verification before use

The candidate is tested against the existing Layer-9 fault matrix, plus:

1. Actual strict-versus-incremental synthetic initialization, adaptation, sweeps and complete receipts compare exactly.
2. A repeated scan within one lease does not re-run old pair validators.
3. A new lease on the same object revalidates the full prefix.
4. Read-only scans outside the writer lease never use the cache.
5. Mutated transaction, genesis and projection files during the lease fail closed.
6. Existing interrupted-write, atomic publication, prepared-pair recovery, corruption, projection conflict, cadence, RNG and non-replay cases continue to run.

Fresh-process crash workers in the inherited suite use the original strict controller. This verifies strict-writer to incremental-recovery compatibility, not process-kill behavior inside the new incremental path. A separate incremental crash worker and Linux GPFS validation are required before deployment. A two-sweep fixture also does not establish long-chain scaling; longer synthetic prefix/count and measured performance checks remain required.

## Live-job migration is a separate gate

The current jobs authenticate their exact generating commit and checkpoint software contracts. Merely changing their launcher to this code would not be a valid exact continuation. Do not edit those immutable specs or checkpoints. Before migration, specify an authenticated code-upgrade boundary that preserves target, spectral chart, current state, frozen tuning and all RNG streams while retaining old software provenance. It must not accidentally retune, reseed, repeat a committed sweep, pool duplicate alternatives or lose current work. No migration is implemented or authorized by this proposal alone.
