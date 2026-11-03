"""Linux x86_64 no-replace namespace publication; no numerical operations."""
import ctypes
import errno
import platform


def rename_noreplace(source, destination):
    """Fail closed if the kernel/filesystem cannot provide RENAME_NOREPLACE."""
    if platform.system() != 'Linux' or platform.machine() != 'x86_64':
        raise RuntimeError('Only Linux x86_64 publication is supported')
    import os
    libc = ctypes.CDLL(None, use_errno=True)
    # x86_64 Linux syscall table: renameat2=316. This also supports glibc 2.17,
    # which predates the libc wrapper. Never fall back to overwriting rename.
    syscall = libc.syscall
    syscall.restype = ctypes.c_long
    result = syscall(ctypes.c_long(316), ctypes.c_int(-100),
                     ctypes.c_char_p(os.fsencode(source)), ctypes.c_int(-100),
                     ctypes.c_char_p(os.fsencode(destination)), ctypes.c_uint(1))
    if result != 0:
        error = ctypes.get_errno()
        if error in (errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP):
            raise RuntimeError('Filesystem/kernel lacks atomic no-replace publication')
        raise OSError(error, os.strerror(error), str(destination))
