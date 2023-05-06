from .view import *
from collections import defaultdict

class DummyBinding():
    def __init__(self, value):
        self.value = value

class AttrBinding():
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
        try:
            setattr(self.state, self.key, self.func(value))
        except:
            pass

class KeyBinding():
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
        try:
            self.state[self.key] = self.func(value)
        except:
            pass

def _notify(listeners, key):
    tbd = []
    for l in listeners[key]:
        if l.retired:
            tbd.append(l)
    for l in tbd:
        listeners[key].remove(l)
    for l in listeners[key]:
        l.redraw()

class BaseState():
    pass

def State(data=None):
    if data is None:
        return StateObject()
    if isinstance(data, list):
        return StateList(data)
    if isinstance(data, dict):
        return StateDict(data)
    return StateObject(data)

class StateObject(BaseState):
    def __init__(self, values=None):
        self.__listeners = defaultdict(set)
        self.__callbacks = defaultdict(set)
        if values is None:
            self.__values = BaseState()
        else:
            self.__values = values

    def __call__(self, key, callback=None):
        if callback is None:
            return AttrBinding(self, key)
        else:
            self.__callbacks[key].add(callback)

    def __getattr__(self, key):
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners[key].add(view)
            except PuiViewNotFoundError:
                pass
        return getattr(self.__values, key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if type(value) is list:
                value = StateList(value)
            elif type(value) is dict:
                value = StateDict(value)
            if not hasattr(self.__values, key) or getattr(self.__values, key) != value:
                setattr(self.__values, key, value)
                _notify(self.__listeners, key)
                for cb in self.__callbacks[key]:
                    cb(value)

    def __repr__(self):
        return f"StateObject({self.__values.__repr__()})"

class StateList(BaseState):
    def __init__(self, values=None):
        self.__listeners = defaultdict(set)
        self.__callbacks = defaultdict(set)
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def __call__(self, key, callback=None):
        if callback is None:
            return KeyBinding(self, key)
        else:
            self.__callbacks[key].add(callback)

    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners[None if isinstance(key, slice) else key].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values[key]

    def __setitem__(self, key, value):
        new = key >= len(self.__values)
        if new or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__listeners, key)
            for cb in self.__callbacks[key]:
                cb(value)
            if new:
                for cb in self.__callbacks[None]:
                    cb(value)

    def __len__(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        n = len(self.__values)
        return n

    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    def append(self, obj):
        self.__values.append(obj)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def clear(self):
        self.__values.clear()
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def count(self, value):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.count(value)

    def extend(self, iterable):
        self.__values.extend(iterable)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def index(self, value, *args, **kwargs):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.index(value, *args, **kwargs)

    def insert(self, index, object):
        self.__values.insert(index, object)
        _notify(self.__listeners, None)
        _notify(self.__listeners, index)
        for cb in self.__callbacks[index]:
            cb(object)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def pop(self, index=-1):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
            self.__listeners[index].add(view)
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(index)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[index]:
            cb(self.__values)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def remove(self, value):
        self.__values.remove(value)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def reverse(self, value):
        self.__values.reverse(value)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)


    def sort(self, *args, **kwargs):
        self.__values.sort(*args, **kwargs)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def get(self, index, default=None):
        try:
            view = find_puiview()
            self.__listeners[index].add(view)
        except PuiViewNotFoundError:
            pass
        if index >= 0 and index < len(self.__values):
            return self.__values[index]
        else:
            return default

    def range(self):
        return range(len(self.__values))

class StateDict(BaseState):
    def __init__(self, values=None):
        self.__listeners = defaultdict(set)
        self.__callbacks = defaultdict(set)
        if values is None:
            self.__values = {}
        else:
            self.__values = values

    def __call__(self, key, callback=None):
        if callback is None:
            return KeyBinding(self, key)
        else:
            self.__callbacks[key].add(callback)

    def __delitem__(self, key):
        self.__values.__delitem__(key)
        _notify(self.__listeners, None)
        _notify(self.__listeners, key)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners[key].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values[key]

    def __getattr__(self, key):
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners[key].add(view)
            except PuiViewNotFoundError:
                pass
        return getattr(self.__values, key)

    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    def __setitem__(self, key, value):
        if not key in self.__values or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__listeners, None)
            _notify(self.__listeners, key)
        for cb in self.__callbacks[key]:
            cb(value)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def clear(self):
        self.__values.clear()
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def get(self, key, default=None):
        try:
            view = find_puiview()
            self.__listeners[key].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.get(key, default)

    def items(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.items()

    def keys(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.keys()

    def pop(self, key, default=None):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(key, default)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def setdefault(self, key, default=None):
        r = self.__values.setdefault(key, default)
        _notify(self.__listeners, None)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def values(self):
        try:
            view = find_puiview()
            self.__listeners[None].add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.values()
