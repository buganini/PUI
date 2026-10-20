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
