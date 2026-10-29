"""Imperative, blocking browser dialogs; not declarative UI nodes."""
from __future__ import annotations
from .._browser import widgets


def _dialog(kind, message, title, default=''):
    runtime = widgets._current_runtime
    if runtime is None or not hasattr(runtime, 'dialog'):
        raise RuntimeError('Web dialogs require an active Web worker')
    return runtime.dialog(kind, str(message), str(title), str(default))


def Information(message: str = 'Information', title: str = 'Information Dialog') -> None:
    """Imperative blocking alert. Return after the browser dismisses it."""
    _dialog('alert', message, title)


def Warning(message: str = 'Warning', title: str = 'Warning Dialog') -> None:
    """Imperative blocking alert, using the browser's native appearance."""
    _dialog('alert', message, title)


def Critical(message: str = 'Critical', title: str = 'Critical Dialog') -> None:
    """Imperative blocking alert, using the browser's native appearance."""
    _dialog('alert', message, title)


def Confirm(message: str = 'Confirm', title: str = 'Confirm Dialog') -> bool:
    """Imperative blocking confirmation; return True for OK, False for Cancel."""
    return _dialog('confirm', message, title)


def Prompt(prompt: str = 'Input', title: str = 'Input Dialog', default: str = '') -> str | None:
    """Imperative blocking prompt; return text (including '') or None on Cancel."""
    return _dialog('prompt', prompt, title, default)


def SaveFile(default=None, title='Save File', dir=None, types=None):
    """Select a download staging path or a server file; return None on cancellation.

    The caller writes the returned path. Download selections appear in the browser
    download shelf. Server selections respect start(webroot=...) when configured.
    """
    runtime = widgets._current_runtime
    if runtime is None or not hasattr(runtime, 'file_picker'):
        raise RuntimeError('Web SaveFile requires an active Web worker')
    try:
        return runtime.file_picker.save(runtime.dialog, default, title, dir, types)
    except ConnectionError:
        return None


def _open(mode, title, dir, types, directory):
    import uuid
    from .._browser.file_selection import initial_directory
    from ..file_filter import patterns as filter_patterns
    initial = initial_directory(dir, directory)
    patterns = filter_patterns(types)
    runtime = widgets._current_runtime
    if runtime is None or not hasattr(runtime, 'file_picker'):
        raise RuntimeError('Web file dialogs require an active Web worker')
    token = uuid.uuid4().hex
    try:
        runtime.file_upload_access(dict(token=token, mode=mode, patterns=patterns))
        return runtime.file_picker.open(runtime.dialog, mode, title, initial, types, runtime.uploads, token)
    except ConnectionError:
        return None
    finally:
        runtime.file_upload_access(None)


def OpenDirectory(title='Open Directory', dir=None, *, directory=None):
    return _open('directory', title, dir, None, directory)


def OpenFile(title='Open File', dir=None, types=None, *, directory=None):
    return _open('file', title, dir, types, directory)


def OpenFiles(title='Open Files', dir=None, types=None, *, directory=None):
    return _open('files', title, dir, types, directory)
