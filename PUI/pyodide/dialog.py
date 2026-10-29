"""Synchronous local file selection using Pyodide's JSPI stack switching."""
from pathlib import Path
from .._browser import widgets
from .._browser.downloads import filename


def SaveFile(default=None, title='Save File', dir=None, types=None):
    """Return a temporary virtual filesystem path for a browser download.

    Requires JSPI. dir and types are accepted for shared application code;
    downloads always use session storage and the user-entered filename.
    """
    from pyodide.ffi import can_run_sync, run_sync
    from _pui_bridge import choose_file
    runtime = widgets._current_runtime
    if runtime is None or runtime.closed:
        raise RuntimeError('Pyodide SaveFile requires an active runtime')
    if not can_run_sync():
        raise RuntimeError('Pyodide SaveFile requires browser JSPI support and an asynchronous Python entrypoint')
    proposed = Path(str(default)).name if default else ''
    error = ''
    while True:
        value = run_sync(choose_file(str(title), proposed, error))
        if value is None:
            return None
        proposed = str(value)
        try:
            return runtime.downloads.allocate(filename(proposed))
        except (ValueError, OSError) as exc:
            error = str(exc)
