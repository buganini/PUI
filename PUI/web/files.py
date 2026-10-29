"""Server-side SaveFile selection and session-owned download destinations."""
import atexit
import fnmatch
import os
from pathlib import Path
import tempfile
import uuid

from .._browser.uploads import remove


def resolve_webroot(value):
    if value is None:
        return None
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('webroot must be a directory')
    return str(root)


class DownloadStore:
    def __init__(self, root=None):
        self.root = Path(root or tempfile.mkdtemp(prefix='pui-download-'))
        atexit.register(self.close)

    def allocate(self, name):
        name = filename(name)
        folder = self.root / uuid.uuid4().hex
        folder.mkdir(parents=True, mode=0o700)
        return str(folder / name)

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


class FilePicker:
    def __init__(self, webroot=None, start=None, downloads=None):
        self.root = Path(resolve_webroot(webroot)) if webroot is not None else None
        self.start = self.root or Path(start or Path.cwd()).resolve()
        self.downloads = downloads

    def path(self, value):
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.start / path
        path = path.resolve()
        if self.root is not None and path != self.root and self.root not in path.parents:
            raise ValueError('The path is outside webroot.')
        return path

    def listing(self, directory, patterns, offset=0):
        directory = self.path(directory)
        if not directory.is_dir():
            raise ValueError('Choose an existing directory.')
        entries = []
        for entry in directory.iterdir():
            try:
                resolved = self.path(entry)
                is_dir = resolved.is_dir()
                if not is_dir and not resolved.is_file():
                    continue
                if not is_dir and patterns and not any(fnmatch.fnmatch(entry.name, p) for p in patterns):
                    continue
                entries.append(dict(name=entry.name, path=str(entry), directory=is_dir))
            except (OSError, ValueError, RuntimeError):
                continue
        entries.sort(key=lambda e: (not e['directory'], e['name'].casefold()))
        offset = min(offset, max(0, (len(entries)-1)//200*200))
        parent = None if directory == self.root or directory.parent == directory else str(directory.parent)
        return dict(directory=str(directory), parent=parent, entries=entries[offset:offset+200],
                    offset=offset, total=len(entries))

    def save(self, ask, default=None, title='Save File', dir=None, types=None):
        # Each request is answered on the transport loop while the application
        # callback waits. No browser-supplied path bypasses these checks.
        def dialog(stage, **options):
            return ask('savefile', '', str(title), '', dict(stage=stage, **options))
        choice = dialog('choice')
        if choice is None or choice['action'] not in ('download', 'save'):
            return None
        proposed = Path(str(default)).name if default else ''
        if choice['action'] == 'download':
            error = ''
            while True:
                answer = dialog('name', name=proposed, error=error)
                if answer is None or answer['action'] != 'confirm':
                    return None
                proposed = answer['value']
                try:
                    return self.downloads.allocate(filename(proposed))
                except (OSError, ValueError) as exc:
                    error = str(exc)
        directory, error, offset = self.start, '', 0
        initial = dir if dir is not None else (str(Path(str(default)).parent) if default and Path(str(default)).parent != Path('.') else self.start)
        try:
            directory = self.path(initial)
            if not directory.is_dir():
                raise ValueError('Choose an existing directory.')
        except (OSError, ValueError, RuntimeError) as exc:
            directory, error = self.start, str(exc)
        # Accept the same Qt and wx filter spellings as native file dialogs.
        parts = str(types or '').replace(';;', '|').split('|')
        if types and all('(' in part and part.endswith(')') for part in parts):
            patterns = [p for part in parts for p in part.rsplit('(', 1)[1][:-1].split()]
        elif types:
            if len(parts) % 2:
                raise ValueError('File filters require label/pattern pairs')
            patterns = [p for group in parts[1::2] for p in group.replace(';', ' ').split()]
        else:
            patterns = []
        while True:
            try:
                listing = self.listing(directory, patterns, offset)
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
                listing = dict(directory=str(directory), parent=None, entries=[], offset=0, total=0)
            answer = dialog('browse', name=proposed, error=error, filter=str(types or ''), **listing)
            if answer is None:
                return None
            error = ''
            action, value = answer['action'], answer['value']
            if action in ('browse', 'page') and 'name' in answer:
                proposed = answer['name']
            try:
                if action == 'browse':
                    target = self.path(value)
                    if not target.is_dir():
                        raise ValueError('Choose an existing directory.')
                    # Check readability before replacing the current directory.
                    self.listing(target, patterns)
                    directory, offset = target, 0
                elif action == 'page':
                    offset = max(0, int(value))
                elif action == 'confirm':
                    proposed = value
                    target = self.path(directory / filename(value))
                    if target.exists():
                        if not target.is_file():
                            raise ValueError('The selected path is not a regular file.')
                        answer = dialog('overwrite', path=str(target))
                        if answer is None or answer['action'] != 'confirm':
                            return None
                        # Recheck symlinks and existence after user interaction.
                        target = self.path(directory / filename(value))
                        if target.exists() and not target.is_file():
                            raise ValueError('The selected path is not a regular file.')
                    if not target.parent.is_dir():
                        raise ValueError('The destination directory no longer exists.')
                    return str(target)
                else:
                    return None
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
