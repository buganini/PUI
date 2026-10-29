"""Temporary download storage shared by Web and browser-local Python."""
import atexit
import json
import os
from pathlib import Path
import tempfile
import time
import stat
import uuid
from .uploads import remove


class DownloadStore:
    def __init__(self, root=None):
        self.root = Path(root or tempfile.mkdtemp(prefix='pui-download-'))
        atexit.register(self.close)

    def allocate(self, name):
        name = filename(name)
        folder = self.root / uuid.uuid4().hex
        folder.mkdir(parents=True, mode=0o700)
        record = dict(id=folder.name, name=name, created=time.time())
        temporary = self.root / (folder.name + '.tmp')
        temporary.write_text(json.dumps(record), encoding='utf-8')
        temporary.replace(self.root / (folder.name + '.json'))
        return str(folder / name)

    def record(self, key):
        if len(key) != 32 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError('Invalid download ID')
        path = self.root / (key + '.json')
        if path.is_symlink():
            raise ValueError('Invalid download metadata')
        record = json.loads(path.read_text(encoding='utf-8'))
        filename(record['name'])
        if record['id'] != key or type(record['created']) not in (float, int):
            raise ValueError('Invalid download metadata')
        return record

    def open(self, key):
        record = self.record(key)
        folder = self.root / key
        path = folder / record['name']
        if self.root.is_symlink() or folder.is_symlink() or path.is_symlink():
            raise ValueError('Download symlinks are not allowed')
        # On platforms with openat, anchor each step to a directory descriptor;
        # a concurrent rename/symlink replacement cannot escape the staging area.
        if os.open in os.supports_dir_fd:
            flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
            root_fd = os.open(self.root, flags)
            try:
                folder_fd = os.open(key, flags, dir_fd=root_fd)
                try:
                    fd = os.open(record['name'], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=folder_fd)
                finally:
                    os.close(folder_fd)
            finally:
                os.close(root_fd)
            stream = os.fdopen(fd, 'rb')
        else:
            if not path.is_file():
                raise FileNotFoundError(path)
            stream = path.open('rb')
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            stream.close()
            raise ValueError('Download is not a regular file')
        return record, stream, info.st_size

    def entries(self, keys=None, include_size=True):
        result = []
        if keys is None:
            keys = [p.stem for p in self.root.glob('*.json')]
        for key in keys:
            try:
                record = self.record(key)
                try:
                    size = None
                    if include_size:
                        _, stream, size = self.open(key)
                        stream.close()
                except (OSError, ValueError):
                    size = None
                result.append(dict(record, size=size))
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return sorted(result, key=lambda r: r['created'])

    def close(self):
        try:
            remove(self.root)
        except OSError:
            import logging
            logging.getLogger('PUI').warning('Could not clean download directory %s', self.root)
        atexit.unregister(self.close)


def filename(value):
    if (not isinstance(value, str) or not value.strip() or value in ('.', '..') or
            any(c in value for c in '/\\\0') or len(value) > 255 or Path(value).is_absolute()):
        raise ValueError('Enter a file name without a directory path.')
    if os.name == 'nt' and (any(c in value for c in ':*?"<>|') or value.endswith((' ', '.'))):
        raise ValueError('This file name is not supported by the server.')
    return value


