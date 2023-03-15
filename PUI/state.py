import inspect
from .view import *

class MutableWrapper():
    def __init__(self, parent, key):
        self.parent = parent
        self.key = key
        dt = type(getattr(self.parent, self.key))
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
        return getattr(self.parent, self.key)

    @value.setter
    def value(self, value):
        try:
            setattr(self.parent, self.key, self.func(value))
        except:
            pass

class BaseState():
    pass

class State(BaseState):
    def __init__(self):
        self.__listeners = set()

    def __getattribute__(self, key):
        if not key.startswith("_"):
            try:
                root, parent = find_pui()
                self.__listeners.add(root)
            except:
                pass
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        if type(value) is list:
            value = StateList(value)
        object.__setattr__(self, key, value)
        for l in self.__listeners:
            l.update()

    def __call__(self, key):
        return MutableWrapper(self, key)

class StateList(BaseState):
    def __init__(self, values):
        self.__values = values
        self.__listeners = set()

    def __getitem__(self, key):
        try:
            root, parent = find_pui()
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
            root, parent = find_pui()
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
        self.__values.pop(index)
        for l in self.__listeners:
            l.update()

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
