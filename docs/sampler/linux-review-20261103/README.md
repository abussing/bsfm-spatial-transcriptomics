# Layer-9 Linux validation candidate

This additive portability review leaves accepted Layers 1-8, scientific
configuration, fixture values, tolerances and stochastic chronology unchanged.
It does not accept Layer 9 or authorize an S10/holdout scientific fit.

Linux uses a nonblocking flock for cooperating writer ownership, released by
the OS on process death, and x86_64 renameat2(RENAME_NOREPLACE) for namespace
publication. Missing kernel/filesystem support fails closed. The syscall is
used because HPC glibc predates its libc wrapper. This is process-interruption
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

The job first authenticates the environment and tests storage on GPFS. Only
after that passes does it run all focused Layer-9 tests, including real
synthetic initialization, 20-step adaptation per factor, complete sweeps and
fresh-process interruption/restart. It then runs unchanged accepted sampler/
provenance and canonical mesh checks, preserving failures and skips. Source
hashes and stage reports are retained externally. A timeout is incomplete,
never a pass. Frozen Windows-fixture differences are not silently relaxed.

References: [Linux syscall table](https://github.com/torvalds/linux/blob/master/arch/x86/entry/syscalls/syscall_64.tbl),
[rename semantics](https://man7.org/linux/man-pages/man2/rename.2.html).
