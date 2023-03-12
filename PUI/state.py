import inspect
from .view import *

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