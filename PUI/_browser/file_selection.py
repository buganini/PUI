"""Shared file-picker arguments and upload path validation."""
import fnmatch
from pathlib import PurePosixPath


def initial_directory(dir, directory):
    if dir is not None and directory is not None and str(dir) != str(directory):
        raise ValueError('Use either dir or directory, or matching values')
    return directory if directory is not None else dir


def matches(name, patterns):
    return not patterns or any(fnmatch.fnmatch(name, p) for p in patterns)


def relative_name(name, mode):
    if (type(name) is not str or not name or len(name) > 1024 or
            any(c in name for c in '\\\x00:') or any(ord(c) < 32 for c in name)):
        raise ValueError('Invalid upload path')
    parts = name.split('/')
    if any(p in ('', '.', '..') or p.endswith((' ', '.')) for p in parts):
        raise ValueError('Invalid upload path')
    # Reject Windows device names too, so a client cannot create special files.
    for part in parts:
        stem = part.split('.')[0].upper()
        if stem in {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}:
            raise ValueError('Reserved upload name')
    if mode == 'directory' and len(parts) < 2:
        raise ValueError('Choose a folder, not individual files')
    if mode != 'directory' and len(parts) != 1:
        raise ValueError('Choose files, not a folder')
    return str(PurePosixPath(*parts))
