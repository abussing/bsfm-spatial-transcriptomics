# Layer-9 Linux validation candidate

This additive portability review leaves accepted Layers 1-8, scientific
configuration, fixture values, tolerances and stochastic chronology unchanged.
It does not accept Layer 9 or authorize an S10/holdout scientific fit.

Linux uses a nonblocking flock for cooperating writer ownership, released by
the OS on process death, and x86_64 renameat2(RENAME_NOREPLACE) for namespace
publication where supported. GPFS rejects this flag; on that filesystem the
fallback requires the current process/context to hold the OS writer lock for
both source and destination. It checks destination absence and performs atomic
same-filesystem rename while ownership excludes cooperating competitors.
It never enables an unowned fallback or claims safety against external actors
ignoring the lock. The syscall is used because HPC glibc predates its wrapper.
This is process-interruption
recovery, not a machine-power-loss durability claim. GPFS support must be
tested on the actual compute node; local Windows results cannot establish it.

Linux environment authentication binds the committed successful build receipt,
package report, interpreter bytes, exact package closure, authenticated runtime
wheels and installed wheel members/RECORDs. The locally built ml_dtypes wheel
is authenticated by its recorded build hash. No Windows lock is rewritten.
Bootstrap pip/setuptools are checked by installed RECORD, as explicitly
recorded in the returned limitations. No package install occurs in validation.

New local Windows tests: six passed and one Linux-only syscall test skipped.
They exercise fresh-process exclusion, lock release after death, immutable
publication and corrupted wheel/member rejection. Full Linux validation is
pending the bounded synthetic job specified here.

Job 22013411 stopped at environment authentication before numerical tests:
pip regenerated NumPy's wheel-bundled `conv_template.cpython-311.pyc` for its
installed path. Source and all other wheel members matched. The correction
validates regenerated code objects against compilation of source bytes inside
the authenticated wheel, rather than exempting bytecode. A mutation test
rejects changed executable code. Updated local result: seven passed, one
Linux-only test skipped. The original failure receipt is retained unchanged.

Job 22013412 passed wheel/source verification and then found the corresponding
stale NumPy RECORD entry: it still records the wheel's pre-install bytecode hash
and size. The corrected check permits this only when RECORD exactly matches
the original authenticated wheel member and the installed code has independently
matched compilation of that wheel's source. Other RECORD mismatches still fail.

Job 22013413 passed full environment authentication and seven of eight storage
tests, including fresh-process exclusion/death and bytecode integrity. GPFS
rejected RENAME_NOREPLACE on a new destination; numerical stages did not start.
The ownership-required fallback above preserves the approved single-writer
transaction design and one atomic directory rename. Tests explicitly reject
unowned/outside-root fallback and existing empty destinations.

While job 22013414 ran at a496b7c, a final path review added normalization of
dot-dot components before testing writer-root containment. Its local regression
passed (eight portability tests passed, two Linux-only tests skipped). This
small guard is separately tested by storage.sbatch; do not attribute it to the
earlier full-sampler run. No numerical operation or transition changed.

The job first authenticates the environment and tests storage on GPFS. Only
after that passes does it run all focused Layer-9 tests, including real
synthetic initialization, 20-step adaptation per factor, complete sweeps and
fresh-process interruption/restart. It then runs unchanged accepted sampler/
provenance and canonical mesh checks, preserving failures and skips. Source
hashes and stage reports are retained externally. A timeout is incomplete,
never a pass. Frozen Windows-fixture differences are not silently relaxed.

References: [Linux syscall table](https://github.com/torvalds/linux/blob/master/arch/x86/entry/syscalls/syscall_64.tbl),
[rename semantics](https://man7.org/linux/man-pages/man2/rename.2.html).
