"""Linux x86_64 no-replace namespace publication; no numerical operations."""
import ctypes
import errno
import platform


def rename_noreplace(source, destination, *, writer_owned=False):
    """No replacement among cooperating writers; GPFS requires held run lock."""
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Only Linux x86_64 publication is supported')
    import os
    libc = ctypes.CDLL(None, use_errno=True)
    # x86_64 Linux syscall table: renameat2=316. This also supports glibc 2.17,
    # which predates the libc wrapper. Unsupported filesystems require the
    # existing single-cooperating-writer protocol, never an unowned fallback.
    syscall = libc.syscall
    syscall.restype = ctypes.c_long
    result = syscall(ctypes.c_long(316), ctypes.c_int(-100),
                     ctypes.c_char_p(os.fsencode(source)), ctypes.c_int(-100),
                     ctypes.c_char_p(os.fsencode(destination)), ctypes.c_uint(1))
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            if not writer_owned:
                raise RuntimeError('Filesystem publication requires exclusive run ownership')
            if os.path.lexists(destination):
                raise FileExistsError(errno.EEXIST, os.strerror(errno.EEXIST), str(destination))
            # The held writer lease excludes every cooperating publisher for
            # this root. Check+rename is serialized by that lease; rename is
            # still the single namespace commit point. Uncooperating external
            # mutation and machine/filesystem power loss are outside scope.
            os.rename(source,destination)
            return
        raise OSError(error, os.strerror(error), str(destination))
