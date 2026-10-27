from .view import *
from collections import defaultdict, deque
from functools import wraps as _wraps
from threading import RLock as _RLock, local as _local
from types import FunctionType as _FunctionType
import logging as _logging


class _StateAccess:
    """One process-wide State lock; notification batches belong to a thread.

    Sharing a lock also covers aliased children and separately constructed State
    containers. Ordinary operations use a short scope; `with state` holds it
    across a whole read/modify/write transaction. No UI redraw or change callback
    runs while this lock is held.
    """
    def __init__(self):
        self.lock = _RLock()
        self.local = _local()

    def __enter__(self):
        self.lock.acquire()
        depth = getattr(self.local, 'depth', 0)
        if depth == 0:
            self.local.views = set()
            self.local.changes = []
        self.local.depth = depth + 1

    def __exit__(self, exc_type, exc, tb):
        self.local.depth -= 1
        outermost = self.local.depth == 0
        if outermost:
            views, changes = self.local.views, self.local.changes
            del self.local.views, self.local.changes
        self.lock.release()
        if outermost:
            if getattr(self.local, 'flushing', False):
                self.local.pending_changes.extend(changes)
                self.local.pending_views.update(views)
                return False
            self.local.flushing = True
            self.local.pending_changes = deque(changes)
            self.local.pending_views = set(views)
            # Reentrant writes append after already committed notifications.
            # Drain callbacks before redraws so derived State reaches its final
            # value without recursive dispatch or duplicate pending redraws.
            error = None
            try:
                while self.local.pending_changes or self.local.pending_views:
                    while self.local.pending_changes:
                        callback, value = self.local.pending_changes.popleft()
                        try:
                            callback(value)
                        except Exception as failure:
                            if error is None:
                                error = failure
                    views = tuple(self.local.pending_views)
                    self.local.pending_views.clear()
                    for view in views:
                        try:
                            if not view.retired_by and not view.destroyed:
                                view.redraw()
                        except Exception as failure:
                            if error is None:
                                error = failure
            finally:
                self.local.flushing = False
                del self.local.pending_changes, self.local.pending_views
            if error is not None:
                if exc_type is None:
                    raise error
                _logging.getLogger('PUI.state').error(
                    'State notification failed while propagating a transaction error',
                    exc_info=(type(error), error, error.__traceback__))
        return False


_state_access = _StateAccess()


def _guarded(method):
    @_wraps(method)
    def call(*args, **kwargs):
        with _state_access:
            return method(*args, **kwargs)
    return call


def _synchronized(cls):
    """Guard the State/Binding API in one place, including property access."""
    for name, member in list(vars(cls).items()):
        if isinstance(member, _FunctionType):
            setattr(cls, name, _guarded(member))
        elif isinstance(member, property):
            setattr(cls, name, property(
                _guarded(member.fget) if member.fget else None,
                _guarded(member.fset) if member.fset else None,
                _guarded(member.fdel) if member.fdel else None,
                member.__doc__))
    return cls


def _changed(callbacks, value):
    # Structural callbacks get a stable shallow snapshot, not mutable backing
    # storage which another thread could change after the lock is released.
    if not callbacks:
        return
    if isinstance(value, list):
        value = list(value)
    elif isinstance(value, dict):
        value = value.copy()
    _state_access.local.changes.extend((callback, value) for callback in tuple(callbacks))


def _subscribe(value, view):
    if isinstance(value, StateObject):
        value._StateObject__listeners[None].add(view)
    elif isinstance(value, StateList):
        value._StateList__listeners.add(view)
    elif isinstance(value, StateDict):
        value._StateDict__listeners.add(view)


class StateMutationInViewBuilderError(Exception):
    pass

class DummyBinding():
    def __init__(self, value):
        self.value = value

class BaseBinding():
    def ref(self, name: str):
        """Publish this binding through the current backend during content()."""
        if not isinstance(name, str) or not name:
            raise ValueError('State ref name must be a nonempty string')
        try:
            view = find_puiview()
        except PuiViewNotFoundError:
            return self
        view._publish_state_ref(name, self.value)
        return self

@_synchronized
class AttrBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except:
            pass
        self.state = state
        self.key = key
        dt = type(getattr(self.state, self.key))
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        return getattr(self.state, self.key)

    @value.setter
    def value(self, value):
        try: # skip validation error
            setattr(self.state, self.key, None if value is None else self.func(value))
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateObject__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateObject__binders")[self.key] = None
        setattr(getattr(self.state, "_StateObject__values"), self.key, getter())
        getattr(self.state, "_StateObject__binders")[self.key] = (getter, setter)

    def emit(self):
        listeners = set()
        for l in getattr(self.state, "_StateObject__listeners").values():
            listeners.update(l)
        _notify(listeners)

@_synchronized
class ListBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except PuiViewNotFoundError:
            pass
        self.state = state
        self.key = key
        dt = type(self.state[self.key])
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        try: # skip validation error
            return self.state[self.key]
        except:
            pass

    @value.setter
    def value(self, value):
        self.state[self.key] = None if value is None else self.func(value)

    def change(self, callback):
        getattr(self.state, "_StateList__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateList__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateList__binders")[self.key] = (getter, setter)

    def emit(self):
        _notify(getattr(self.state, "_StateList__listeners"))

@_synchronized
class DictBinding(BaseBinding):
    def __init__(self, state, key):
        try:
            self.viewroot = find_puiview()
            self.viewparent = self.viewroot.frames[-1]
        except PuiViewNotFoundError:
            pass
        self.state = state
        self.key = key
        dt = type(self.state[self.key])
        if dt is str:
            self.func = str
        elif dt is int:
            self.func = int
        elif dt is float:
            self.func = float
        else:
            self.func = lambda x:x

    @property
    def value(self):
        return self.state[self.key]

    @value.setter
    def value(self, value):
        try: # skip validation error
            self.state[self.key] = None if value is None else self.func(value)
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateDict__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateDict__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateDict__binders")[self.key] = (getter, setter)

    def emit(self):
        _notify(getattr(self.state, "_StateDict__listeners"))

def _notify(listeners):
    retired = {view for view in listeners if view.retired_by or view.destroyed}
    listeners.difference_update(retired)
    _state_access.local.views.update(listeners)


class BaseState:
    def __enter__(self):
        _state_access.__enter__()
        return self

    def __exit__(self, exc_type, exc, tb):
        return _state_access.__exit__(exc_type, exc, tb)


@_guarded
def Unstate(data):
    if isinstance(data, StateList):
        return [Unstate(item) for item in data._StateList__values]
    elif isinstance(data, StateDict):
        return {k: Unstate(v) for k, v in data._StateDict__values.items()}
    else:
        return data

def _state(data):
    if isinstance(data, list):
        return StateList([_state(item) for item in data])
    elif isinstance(data, dict):
        return StateDict({k: _state(v) for k, v in data.items()})
    else:
        return data

def State(data=None, deep=False):
    if data is None:
        return StateObject()
    if isinstance(data, list):
        if deep:
            return StateList([_state(item) for item in data])
        else:
            return StateList(data)
    if isinstance(data, dict):
        if deep:
            return StateDict({k: _state(v) for k, v in data.items()})
        else:
            return StateDict(data)
    return StateObject(data)

@_synchronized
class StateObject(BaseState):
    def __init__(self, values=None):
        # Initial storage does not mutate an existing observable value. This
        # permits lazy internal node State creation during content construction.
        object.__setattr__(self, "_StateObject__listeners", defaultdict(set))
        object.__setattr__(self, "_StateObject__callbacks", defaultdict(set))
        object.__setattr__(self, "_StateObject__binders", {})
        if values is None:
            object.__setattr__(self, "_StateObject__values", BaseState())
        else:
            object.__setattr__(self, "_StateObject__values", values)

    def __call__(self, key=None):
        if key is None:
            listeners = set()
            for l in self.__listeners.values():
                listeners.update(l)
            _notify(listeners)
            return
        try:
            view = find_puiview()
            self.__listeners[key].add(view)
        except PuiViewNotFoundError:
            pass
        return AttrBinding(self, key)

    def __eq__(self, other):
        return self.__values == other

    # getter
    def __getattr__(self, key):
        view = None
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners[key].add(view)
            except PuiViewNotFoundError:
                view = None
        ret = getattr(self.__values, key)
        if view:
            _subscribe(ret, view)
        return ret

    # setter
    def __setattr__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)

            if isinstance(value, list):
                value = StateList(value)
            elif isinstance(value, dict):
                value = StateDict(value)
            if not hasattr(self.__values, key) or getattr(self.__values, key) != value:
                setattr(self.__values, key, value)
                _notify(self.__listeners[key])
                _notify(self.__listeners[None])
                _changed(self.__callbacks[key], value)

    # getter
    def __repr__(self):
        return f"StateObject({self.__values.__repr__()})"

@_synchronized
class StateList(BaseState):
    def __init__(self, values=None):
        self.__generation = 0
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def _binding_generation(self, key):
        """Lifetime of index bindings; every structural edit revokes all indices."""
        return self.__generation

    def __call__(self, key=None):
        if key is None:
            _notify(self.__listeners)
            return
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return ListBinding(self, key)

    def __eq__(self, other):
        return self.__values == other

    # getter
    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            view = None

        ret = self.__values[key]
        if view:
            _subscribe(ret, view)
        return ret

    # setter
    def __setitem__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if self.__binders.get(key):
            self.__binders[key][1](value)
        new = key >= len(self.__values)
        if new or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__listeners)
            _changed(self.__callbacks[key], value)
            if new:
                _changed(self.__callbacks[None], value)

    # getter
    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    # getter
    def __len__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return len(self.__values)

    # getter
    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return iter(tuple(self.__values))

    # getter
    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    # setter
    def append(self, obj):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.append(obj)
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # setter
    def clear(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.clear()
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # getter
    def count(self, value):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.count(value)

    # setter
    def extend(self, iterable):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        try:
            self.__values.extend(iterable)
        finally:
            # Iterators can fail after extending part of the list.
            self.__generation += 1
            _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # getter
    def index(self, value, *args, **kwargs):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.index(value, *args, **kwargs)

    # setter
    def insert(self, index, object):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.insert(index, object)
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[index], object)
        _changed(self.__callbacks[None], self.__values)

    # getter/setter
    def pop(self, index=-1):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(index)
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[index], self.__values)
        _changed(self.__callbacks[None], self.__values)
        return r

    # setter
    def remove(self, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.remove(value)
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # setter
    def reverse(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.reverse()
        self.__generation += 1
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)


    # setter
    def sort(self, *args, key=None, reverse=False, **kwargs):
        """Sort in place, forwarding list defaults and any extra arguments."""
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        try:
            self.__values.sort(*args, key=key, reverse=reverse, **kwargs)
        finally:
            # A failed comparison may still leave the list partially reordered.
            self.__generation += 1
            _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # getter
    def get(self, index, default=None):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        if index >= 0 and index < len(self.__values):
            return self.__values[index]
        else:
            return default

    # getter
    def range(self):
        return range(len(self.__values))

@_synchronized
class StateDict(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        if values is None:
            self.__values = {}
        else:
            self.__values = values
        self.__generation = 0
        self.__generations = {}
        self._sync_binding_keys()

    def _sync_binding_keys(self):
        self.__generations = {key: value for key, value in self.__generations.items()
                              if key in self.__values}
        for key in self.__values:
            if key not in self.__generations:
                self.__generation += 1
                self.__generations[key] = self.__generation

    def _binding_generation(self, key):
        """Lifetime of this key, independent of edits to other dictionary keys."""
        return self.__generations.get(key)

    def __call__(self, key=None):
        if key is None:
            _notify(self.__listeners)
            return
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return DictBinding(self, key)

    def __eq__(self, other):
        return self.__values == other

    # setter
    def __delitem__(self, key):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.__delitem__(key)
        self.__generations.pop(key, None)
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # getter
    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            view = None
        ret = self.__values[key]
        if view:
            _subscribe(ret, view)
        return ret

    # getter
    def __getattr__(self, key):
        view = None
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners.add(view)
            except PuiViewNotFoundError:
                view = None
        ret = getattr(self.__values, key)
        if view:
            _subscribe(ret, view)
        return ret

    # setter
    def __setattr__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)
            _notify(self.__listeners)
            return setattr(self.__values, key, value)

    # getter
    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    # getter
    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return iter(tuple(self.__values))

    # getter
    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    # setter
    def __setitem__(self, key, value):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        if self.__binders.get(key):
            self.__binders[key][1](value)
        if not key in self.__values or self.__values[key] != value:
            self.__values[key] = value
            if key not in self.__generations:
                self.__generation += 1
                self.__generations[key] = self.__generation
            _notify(self.__listeners)
        _changed(self.__callbacks[key], value)
        _changed(self.__callbacks[None], self.__values)

    # setter
    def clear(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        self.__values.clear()
        self.__generations.clear()
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    # getter
    def get(self, key, default=None):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.get(key, default)

    # getter
    def items(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.copy().items()

    # getter
    def copy(self):
        return dict(self.items())

    # getter
    def keys(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.copy().keys()

    # getter/setter
    def pop(self, key, default=None):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(key, default)
        self.__generations.pop(key, None)
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)
        return r

    # setter
    def setdefault(self, key, default=None):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        r = self.__values.setdefault(key, default)
        if key not in self.__generations:
            self.__generation += 1
            self.__generations[key] = self.__generation
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)
        return r

    # getter
    def values(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.copy().values()

    def update(self, *args, **kwargs):
        """Forward dict.update call patterns, with reactive lifetime tracking."""
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        try:
            self.__values.update(*args, **kwargs)
        finally:
            self._sync_binding_keys()
            _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)

    def popitem(self):
        try:
            find_puiview()
            raise StateMutationInViewBuilderError()
        except PuiViewNotFoundError:
            pass
        key, value = self.__values.popitem()
        self.__generations.pop(key, None)
        _notify(self.__listeners)
        _changed(self.__callbacks[None], self.__values)
        return key, value
