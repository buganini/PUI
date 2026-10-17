"""Detect edited workspace files without reading their contents."""
import os
from pathlib import Path

IGNORED = frozenset(('.git', 'env', '.venv', 'venv', '__pycache__',
                     '.pytest_cache', '.mypy_cache', '.ruff_cache', 'node_modules'))


def snapshot(directory):
    result = {}
    root = Path(directory)
    for base, directories, files in os.walk(root, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in IGNORED)
        for name in files:
            if name.endswith(('.pyc', '.pyo')):
                continue
            path = Path(base) / name
            try:
                stat = path.lstat()
            except FileNotFoundError:
                continue
            result[str(path.relative_to(root))] = (stat.st_mtime_ns, stat.st_size)
    return result
