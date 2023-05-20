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
        try: # skip validation error
            setattr(self.state, self.key, self.func(value))
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateObject__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateObject__binders")[self.key] = None
        setattr(getattr(self.state, "_StateObject__values"), self.key, getter())
        getattr(self.state, "_StateObject__binders")[self.key] = (getter, setter)

class ListBinding():
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
        self.state[self.key] = self.func(value)

    def change(self, callback):
        getattr(self.state, "_StateList__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateList__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateList__binders")[self.key] = (getter, setter)

class DictBinding():
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
            self.state[self.key] = self.func(value)
        except:
            pass

    def change(self, callback):
        getattr(self.state, "_StateDict__callbacks")[self.key].add(callback)

    def bind(self, getter, setter):
        getattr(self.state, "_StateDict__binders")[self.key] = None
        self.state[self.key] = getter()
        getattr(self.state, "_StateDict__binders")[self.key] = (getter, setter)

def _notify(listeners):
    tbd = []
    for l in listeners:
        if l.retired_by:
            tbd.append(l)
    for l in tbd:
        listeners.remove(l)
    for l in listeners:
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
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        if values is None:
            self.__values = BaseState()
        else:
            self.__values = values

    def __call__(self, key=None):
        return AttrBinding(self, key)

    def __getattr__(self, key):
        if not key.startswith("_"):
            try:
                view = find_puiview()
                self.__listeners.add(view)
            except PuiViewNotFoundError:
                pass
        return getattr(self.__values, key)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)

            if type(value) is list:
                value = StateList(value)
            elif type(value) is dict:
                value = StateDict(value)
            if not hasattr(self.__values, key) or getattr(self.__values, key) != value:
                setattr(self.__values, key, value)
                _notify(self.__listeners)
                for cb in self.__callbacks[key]:
                    cb(value)

    def __repr__(self):
        return f"StateObject({self.__values.__repr__()})"

class StateList(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def __call__(self, key=None):
        return ListBinding(self, key)

    def __getitem__(self, key):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass

        return self.__values[key]

    def __setitem__(self, key, value):
        if self.__binders.get(key):
            self.__binders[key][1](value)
        new = key >= len(self.__values)
        if new or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__listeners)
            for cb in self.__callbacks[key]:
                cb(value)
            if new:
                for cb in self.__callbacks[None]:
                    cb(value)

    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    def __len__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return len(self.__values)

    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    def append(self, obj):
        self.__values.append(obj)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def clear(self):
        self.__values.clear()
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def count(self, value):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.count(value)

    def extend(self, iterable):
        self.__values.extend(iterable)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def index(self, value, *args, **kwargs):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.index(value, *args, **kwargs)

    def insert(self, index, object):
        self.__values.insert(index, object)
        _notify(self.__listeners)
        for cb in self.__callbacks[index]:
            cb(object)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def pop(self, index=-1):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(index)
        _notify(self.__listeners)
        for cb in self.__callbacks[index]:
            cb(self.__values)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def remove(self, value):
        self.__values.remove(value)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def reverse(self, value):
        self.__values.reverse(value)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)


    def sort(self, *args, **kwargs):
        self.__values.sort(*args, **kwargs)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)

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

    def range(self):
        return range(len(self.__values))

class StateDict(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        self.__callbacks = defaultdict(set)
        self.__binders = {}
        if values is None:
            self.__values = {}
        else:
            self.__values = values

    def __call__(self, key=None):
        return DictBinding(self, key)

    def __delitem__(self, key):
        self.__values.__delitem__(key)
        _notify(self.__listeners)
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


    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
        else:
            if self.__binders.get(key):
                self.__binders[key][1](value)
            _notify(self.__listeners)
            return setattr(self.__values, key, value)

    def __bool__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return bool(self.__values)

    def __iter__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.__repr__()

    def __setitem__(self, key, value):
        if self.__binders.get(key):
            self.__binders[key][1](value)
        if not key in self.__values or self.__values[key] != value:
            self.__values[key] = value
            _notify(self.__listeners)
        for cb in self.__callbacks[key]:
            cb(value)
        for cb in self.__callbacks[None]:
            cb(self.__values)

    def clear(self):
        self.__values.clear()
        _notify(self.__listeners)
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
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.items()

    def keys(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.keys()

    def pop(self, key, default=None):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        r = self.__values.pop(key, default)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def setdefault(self, key, default=None):
        r = self.__values.setdefault(key, default)
        _notify(self.__listeners)
        for cb in self.__callbacks[None]:
            cb(self.__values)
        return r

    def values(self):
        try:
            view = find_puiview()
            self.__listeners.add(view)
        except PuiViewNotFoundError:
            pass
        return self.__values.values()
