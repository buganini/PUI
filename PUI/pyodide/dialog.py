"""Synchronous dialogs using Pyodide's JSPI stack switching."""
from pathlib import Path
from .._browser import widgets
from .._browser.downloads import filename


def _dialog(kind, message, title, default=''):
    from pyodide.ffi import can_run_sync, run_sync
    from _pui_bridge import dialog
    runtime = widgets._current_runtime
    if runtime is None or runtime.closed:
        raise RuntimeError('Pyodide dialogs require an active runtime')
    if not can_run_sync():
        raise RuntimeError('Pyodide dialogs require browser JSPI support and an asynchronous Python entrypoint')
    return run_sync(dialog(kind, str(message), str(title), str(default)))


def Information(message='Information', title='Information Dialog'):
    _dialog('information', message, title)


def Warning(message='Warning', title='Warning Dialog'):
    _dialog('warning', message, title)


def Critical(message='Critical', title='Critical Dialog'):
    _dialog('critical', message, title)


def Confirm(message='Confirm', title='Confirm Dialog'):
    return _dialog('confirm', message, title)


def Prompt(prompt='Input', title='Input Dialog', default=''):
    return _dialog('prompt', prompt, title, default)


def SaveFile(default=None, title='Save File', dir=None, types=None):
    """Return a temporary virtual filesystem path for a browser download.

    Requires JSPI. dir and types are accepted for shared application code;
    downloads always use session storage and the user-entered filename.
    """
    runtime = widgets._current_runtime
    proposed = Path(str(default)).name if default else ''
    error = ''
    while True:
        value = _dialog('savefile', error, title, proposed)
        if value is None:
            return None
        proposed = str(value)
        try:
            return runtime.downloads.allocate(filename(proposed))
        except (ValueError, OSError) as exc:
            error = str(exc)
