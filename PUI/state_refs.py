"""Backend publisher defaults and Web subscriptions, separate from node refs."""
import json
import logging
import os
from contextlib import contextmanager
from weakref import WeakKeyDictionary
from .state import StateList, StateDict


def noop_publish(name, value):
    """Forward managed-child State refs; otherwise leave values unpublished."""
    if os.environ.get("PUI_IPC"):
        from .ai.ipc import publish
        publish(name, value)


def _json_value(value):
    # Read through State's public accessors so nested mutations also redraw
    # the declaring view, using the existing dependency tracking.
    if isinstance(value, StateList):
        return list(value)
    if isinstance(value, StateDict):
        return dict(value.items())
    raise TypeError('Not a JSON value')


class StateRefs:
    def __init__(self):
        self._views = WeakKeyDictionary()

    @contextmanager
    def collect(self, view):
        # Independent subview updates replace only their own declarations.
        previous = self._views.get(view)
        self._views[view] = {}
        try:
            yield
        except BaseException:
            # PUIView keeps its previous children when content() fails.
            if previous is None:
                self._views.pop(view, None)
            else:
                self._views[view] = previous
            raise
        else:
            self._views[view] = self._views.pop(view)

    def publish(self, view, name, value):
        try:
            text = json.dumps(value, default=_json_value, ensure_ascii=True,
                              allow_nan=False, separators=(',', ':'))
        except (TypeError, ValueError, OverflowError, RecursionError):
            logging.getLogger('PUI').warning('State ref %r is not JSON serializable; skipping', name)
            return
        self._views.setdefault(view, {})[name] = text

    def snapshot(self):
        values = {}
        for view, entries in list(self._views.items()):
            if view.destroyed or view.retired_by:
                self._views.pop(view, None)
            else:
                values.update(entries)
        return values

    def clear(self):
        self._views.clear()
