"""Server-side SaveFile selection and session-owned download destinations."""
import fnmatch
from pathlib import Path

from .._browser.downloads import DownloadStore, filename
from .._browser.file_selection import filters, matches


def resolve_webroot(value):
    if value is None:
        return None
    root = Path(value).expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError('webroot must be a directory')
    return str(root)


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

    def listing(self, directory, patterns, offset=0, *, directories_only=False):
        directory = self.path(directory)
        if not directory.is_dir():
            raise ValueError('Choose an existing directory.')
        entries = []
        for entry in directory.iterdir():
            try:
                resolved = self.path(entry)
                is_dir = resolved.is_dir()
                if directories_only and not is_dir:
                    continue
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
        patterns = filters(types)
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
        while True:
            try:
                listing = self.listing(directory, patterns, offset)
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
                listing = dict(directory=str(directory), parent=None, entries=[], offset=0, total=0)
            answer = dialog('browse', name=proposed, error=error, filter=' '.join(patterns), **listing)
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

    def open(self, ask, mode, title, dir, types, uploads, token):
        patterns = filters(types)
        directory, offset, error = self.start, 0, ''
        try:
            directory = self.path(dir if dir is not None else self.start)
            self.listing(directory, patterns)
        except (OSError, ValueError, RuntimeError) as exc:
            directory, error = self.start, str(exc)
        while True:
            try:
                listing = self.listing(directory, patterns, offset, directories_only=mode == 'directory')
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
                listing = dict(directory=str(directory), parent=None, entries=[], offset=0, total=0)
            answer = ask('openfile', '', str(title), '', dict(mode=mode, token=token,
                patterns=patterns, error=error, limits=uploads.limits, **listing))
            if answer is None:
                return None
            error = ''
            try:
                action, value = answer['action'], answer['value']
                if action == 'upload':
                    return uploads.take_selection(value, token, mode)
                if action == 'browse':
                    target = self.path(value)
                    self.listing(target, patterns)
                    directory, offset = target, 0
                elif action == 'page':
                    offset = max(0, int(value))
                elif action == 'open':
                    if (mode == 'files' and (type(value) is not list or not all(type(v) is str for v in value))) or (mode != 'files' and type(value) is not str):
                        raise ValueError('Invalid file selection')
                    values = value if mode == 'files' else [value]
                    if not values:
                        raise ValueError('Select at least one file')
                    paths = []
                    for item in values:
                        target = self.path(item)
                        if mode == 'directory':
                            if not target.is_dir():
                                raise ValueError('Choose an existing directory')
                        elif not target.is_file() or not matches(target.name, patterns):
                            raise ValueError('Choose an existing file matching the filter')
                        paths.append(str(target))
                    return paths if mode == 'files' else paths[0]
                else:
                    raise ValueError('Invalid file selection action')
            except (OSError, ValueError, RuntimeError) as exc:
                error = str(exc)
