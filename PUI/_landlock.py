"""Optional filesystem restrictions, applied only at application startup."""
import logging
import os
import sys
from collections.abc import Mapping
from pathlib import Path


def prepare(policy):
    """Validate and freeze an allowlist without restricting the caller."""
    if policy is None:
        return None
    if sys.platform != 'linux':
        logging.getLogger('PUI').warning('Landlock is only available on Linux; ignoring landlock')
        return None
    if not isinstance(policy, Mapping) or set(policy) - {'read', 'write', 'execute'}:
        raise ValueError('landlock must be a mapping with read, write and/or execute paths')
    result = {}
    for key, paths in policy.items():
        if isinstance(paths, (str, bytes, os.PathLike)):
            raise ValueError('landlock paths must be sequences, not a single path')
        result[key] = tuple(str(Path(path).resolve(strict=True)) for path in paths)
    _binding()
    return result


def _binding():
    import ctypes
    import platform
    # The binding uses the generic Linux syscall numbers on these architectures.
    if platform.machine().lower() not in {'x86_64', 'aarch64', 'riscv64'}:
        raise RuntimeError('Landlock is not supported on this architecture by PUI')
    try:
        import landlock
        from landlock import plumbing
    except ImportError as error:
        raise RuntimeError('Install qpuiq[landlock] to use landlock') from error
    ctypes.set_errno(0)
    try:
        abi = landlock.landlock_abi_version()
    except landlock.LandlockError as error:
        raise RuntimeError('Landlock is unavailable or disabled on this Linux kernel') from error
    if abi < 3:
        raise RuntimeError('Landlock requires kernel ABI 3 or newer (including truncate protection)')
    return plumbing


def apply(policy):
    """Irreversibly restrict this thread and future descendants; fail closed."""
    policy = prepare(policy)
    if policy is None:
        return
    import ctypes
    import stat
    api = _binding()
    if len(os.listdir('/proc/self/task')) != 1:
        raise RuntimeError('Apply Landlock before starting background threads')

    def call(function, *args):
        # The binding checks errno, so discard any stale value before each call.
        ctypes.set_errno(0)
        return function(*args)

    access = api.FSAccess
    handled = access.all()
    read = access.READ_FILE | access.READ_DIR
    permissions = {'read': read, 'write': handled & ~access.EXECUTE,
                   'execute': access.EXECUTE}
    attr = api.RulesetAttr(handled)
    fd = call(api.get_create_ruleset(), ctypes.byref(attr), ctypes.sizeof(attr), 0)
    try:
        for kind, paths in policy.items():
            for path in paths:
                parent = os.open(path, os.O_PATH | os.O_CLOEXEC)
                try:
                    allowed = permissions[kind]
                    if not stat.S_ISDIR(os.fstat(parent).st_mode):
                        allowed &= access.all_file()
                    rule = api.PathBeneathAttr(allowed, parent)
                    call(api.get_add_rule(), fd, 1, ctypes.byref(rule), 0)
                finally:
                    os.close(parent)
        call(api.get_prctl(), api.PR_SET_NO_NEW_PRIVS, 1, 0, 0, 0)
        call(api.get_restrict_self(), fd, 0)
    finally:
        os.close(fd)
