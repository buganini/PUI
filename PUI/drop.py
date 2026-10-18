"""Portable inbound drop data. Acceptance never performs file operations."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DropFile:
    name: str
    path: str
    temporary: bool = False


class DropEvent:
    def __init__(self, *, files=(), text=None, urls=(), x=None, y=None, action='copy'):
        self.files = tuple(files)
        self.text = text
        self.urls = tuple(urls)
        self.x, self.y, self.action = x, y, action
        self.accepted = False
        self.reason = 'Drop was not accepted'

    def accept(self):
        self.accepted, self.reason = True, ''

    def reject(self, reason='Drop was rejected'):
        self.accepted, self.reason = False, str(reason)


def extensions(value):
    if value is None:
        return None
    if isinstance(value, str):
        value = (value,)
    value = tuple(value)
    if any(not isinstance(v, str) for v in value):
        raise ValueError('extensions must be strings')
    result = tuple(dict.fromkeys(v.lower() for v in value))
    if not result or any(v != '/' and (not v.startswith('.') or len(v) < 2 or
                         any(c in v for c in '/\\\x00')) for v in result):
        raise ValueError('extensions must contain suffixes such as .json or .tar.gz, or / for directories')
    return result


def check_names(names, allowed):
    if allowed is not None:
        invalid = [name for name in names if not name.lower().endswith(tuple(allowed))]
        if invalid:
            return 'Unsupported file extension: ' + ', '.join(invalid)
    return None


def dispatch(node, event):
    node = node.get_node()
    if node.destroyed or node._onDropped is None or getattr(node, 'disabled', False):
        event.reject('Drop target is no longer available')
        return event
    allowed = node._drop_extensions
    directories, names = [], []
    for file in event.files:
        if Path(file.path).is_dir():
            directories.append(file)
        else:
            names.append(file.name)
    reason = check_names(names, allowed)
    if not reason and directories and allowed is not None and '/' not in allowed:
        reason = 'Directories are not allowed by the extension filter'
    if reason:
        event.reject(reason)
        return event
    callback, args, kwargs = node._onDropped
    try:
        callback(event, *args, **kwargs)
    except Exception:
        event.reject('Drop handler failed')
        raise
    return event
