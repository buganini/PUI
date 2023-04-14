import inspect
from .view import *

class AttrBinding():
    def __init__(self, state, key):
        try:
            root, parent = find_pui()
            self.viewroot = root
            self.viewparent = parent
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
            root, parent = find_pui()
            self.viewroot = root
            self.viewparent = parent
        except:
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
        object.__setattr__(self, "__listeners", set())
        if values is None:
            object.__setattr__(self, "__values", BaseState())
        else:
            object.__setattr__(self, "__values", values)

    def __call__(self, key):
        return AttrBinding(self, key)

    def __getattribute__(self, key):
        if not key.startswith("_"):
            try:
                root, parent, viewkey = find_pui()
                object.__getattribute__(self, "__listeners").add(root)
            except:
                pass
        return getattr(object.__getattribute__(self, "__values"), key)

    def __setattr__(self, key, value):
        if type(value) is list:
            value = StateList(value)
        elif type(value) is dict:
            value = StateDict(value)
        setattr(object.__getattribute__(self, "__values"), key, value)
        for l in object.__getattribute__(self, "__listeners"):
            l.update()

class StateList(BaseState):
    def __init__(self, values=None):
        self.__listeners = set()
        if values is None:
            self.__values = []
        else:
            self.__values = values

    def __call__(self, key):
        return KeyBinding(self, key)

    def __getitem__(self, key):
        try:
            root, parent, viewkey = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values[key]

    def __setitem__(self, key, value):
        self.__values[key] = value
        for l in self.__listeners:
            l.update()

    def __len__(self):
        try:
            root, parent, viewkey = find_pui()
            self.__listeners.add(root)
        except:
            pass
        n = len(self.__values)
        return n

    def __iter__(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.__repr__()

    def append(self, obj):
        self.__values.append(obj)
        for l in self.__listeners:
            l.update()

    def clear(self):
        self.__values.clear()
        for l in self.__listeners:
            l.update()

    def count(self, value):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.count(value)

    def extend(self, iterable):
        self.__values.extend(iterable)
        for l in self.__listeners:
            l.update()

    def index(self, value, *args, **kwargs):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.index(value, *args, **kwargs)

    def insert(self, index, object):
        self.__values.insert(index, object)
        for l in self.__listeners:
            l.update()

    def pop(self, index=-1):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        r = self.__values.pop(index)
        for l in self.__listeners:
            l.update()
        return r

    def remove(self, value):
        self.__values.remove(value)
        for l in self.__listeners:
            l.update()

    def reverse(self, value):
        self.__values.reverse(value)
        for l in self.__listeners:
            l.update()


    def sort(self, *args, **kwargs):
        self.__values.sort(*args, **kwargs)
        for l in self.__listeners:
            l.update()

    def get(self, index, default=None):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
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
        if values is None:
            self.__values = {}
        else:
            self.__values = values

    def __call__(self, key):
        return KeyBinding(self, key)

    def __delitem__(self, key):
        self.__values.__delitem__(key)
        for l in self.__listeners:
            l.update()

    def __getitem__(self, key):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values[key]

    def __iter__(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.__iter__()

    def __repr__(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.__repr__()

    def __setitem__(self, key, value):
        self.__values[key] = value
        for l in self.__listeners:
            l.update()

    def clear(self):
        self.__values.clear()
        for l in self.__listeners:
            l.update()

    def get(self, key, default=None):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.get(key, default)

    def items(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.items()

    def keys(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.keys()

    def pop(self, key):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        r = self.__values.pop(key)
        for l in self.__listeners:
            l.update()
        return r

    def setdefault(self, key, default=None):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        r = self.__values.setdefault(key, default)
        for l in self.__listeners:
            l.update()
        return r

    def values(self):
        try:
            root, parent = find_pui()
            self.__listeners.add(root)
        except:
            pass
        return self.__values.values()
