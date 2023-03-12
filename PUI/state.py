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

class State():
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
        object.__setattr__(self, key, value)
        for l in self.__listeners:
            l.update()

    def __call__(self, key):
        return MutableWrapper(self, key)
