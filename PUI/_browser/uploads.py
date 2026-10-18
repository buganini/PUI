"""Session-local upload storage, shared by HTTP and the Pyodide bridge."""
import atexit
import json
from pathlib import Path
import re
import shutil
import tempfile
import uuid

from ..drop import DropFile, check_names

DEFAULT_LIMITS = dict(max_files=32, max_file_bytes=64 * 1024**2, max_session_bytes=256 * 1024**2)


def limits(value=None):
    result = dict(DEFAULT_LIMITS)
    if value is not None:
        if not isinstance(value, dict) or set(value) - result.keys():
            raise ValueError('Unknown upload_limits setting')
        result.update(value)
    if any(type(v) is not int or not 0 < v <= 2**53 - 1 for v in result.values()):
        raise ValueError('upload_limits values must be positive integers')
    return result


def remove(path):
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


class UploadStore:
    def __init__(self, root=None, upload_limits=None):
        self.root = Path(root or tempfile.mkdtemp(prefix='pui-upload-'))
        self.limits = limits(upload_limits)
        self.active = {}
        atexit.register(self.close)

    def close(self):
        self.active.clear()
        try:
            remove(self.root)
        except OSError:
            # Landlock may deny worker cleanup; the gateway repeats it.
            import logging
            logging.getLogger('PUI').warning('Could not clean upload directory %s', self.root)
        atexit.unregister(self.close)

    def directory(self, key):
        if type(key) is not str or not re.fullmatch('[0-9a-f]{32}', key):
            raise ValueError('Invalid upload ID')
        return self.root / key

    def usage(self):
        # Count current files, so applications can release their quota by deleting them.
        total = 0
        for folder in self.root.glob('*'):
            if folder.is_symlink() or not folder.is_dir():
                continue
            for p in folder.iterdir():
                if p.name != 'manifest.json' and not p.is_symlink():
                    try:
                        total += p.stat().st_size
                    except FileNotFoundError:
                        pass
        return total

    def begin(self):
        key = uuid.uuid4().hex
        self.directory(key).mkdir(parents=True, mode=0o700)
        self.active[key] = []
        return key

    def add(self, key, name, allowed=None):
        records = self.active[key]
        if len(records) >= self.limits['max_files']:
            raise ValueError('Too many files in one drop')
        if type(name) is not str or not name or len(name) > 1024 or any(c in name for c in '/\\\x00'):
            raise ValueError('Invalid file name')
        reason = check_names([name], allowed)
        if reason:
            raise ValueError(reason)
        fid = uuid.uuid4().hex
        records.append(dict(id=fid, name=name))
        (self.directory(key) / (fid + '.part')).touch(mode=0o600)
        return fid

    def write(self, key, fid, data):
        if not any(r['id'] == fid for r in self.active[key]):
            raise ValueError('Unknown upload file')
        path = self.directory(key) / (fid + '.part')
        if path.stat().st_size + len(data) > self.limits['max_file_bytes']:
            raise ValueError('File exceeds upload size limit')
        if self.usage() + len(data) > self.limits['max_session_bytes']:
            raise ValueError('Session upload quota exceeded')
        with path.open('ab') as f:
            f.write(data)

    def finish(self, key):
        folder = self.directory(key)
        records = self.active.pop(key)
        if not records:
            raise ValueError('No files uploaded')
        for r in records:
            (folder / (r['id'] + '.part')).rename(folder / r['id'])
        (folder / 'manifest.json').write_text(json.dumps(records), encoding='utf-8')
        return key

    def take(self, key):
        folder = self.directory(key)
        manifest = folder / 'manifest.json'
        records = json.loads(manifest.read_text(encoding='utf-8'))
        manifest.unlink()  # One-shot delivery; retained accepted files cannot be replayed.
        return [DropFile(r['name'], str(folder / r['id']), True) for r in records]

    def discard(self, key):
        self.active.pop(key, None)
        remove(self.directory(key))

    def discard_pending(self):
        for folder in self.root.glob('*'):
            if (folder / 'manifest.json').is_file() or folder.name in self.active:
                self.discard(folder.name)
