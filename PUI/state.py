import inspect
from .view import *

class State():
    def __init__(self):
        self.__listeners = set()

    def __getattribute__(self, key):
        if not key.startswith("_"):
            parents = inspect.getouterframes(inspect.currentframe())
            for p in parents:
                views = [v for k,v in p.frame.f_locals.items() if isinstance(v, PUIView)]
                if views:
                    self.__listeners.add(views[0])
                    break
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)
        for l in self.__listeners:
            l.update()