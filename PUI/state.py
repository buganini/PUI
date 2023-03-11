import inspect
from .view import *

class State():
    def __init__(self):
        self.__listeners = set()

    def __getattribute__(self, key):
        if not key.startswith("_"):
            frame = inspect.currentframe()
            while frame:
                views = [v for k,v in frame.f_locals.items() if isinstance(v, PUIView)]
                if views:
                    self.__listeners.add(views[0])
                    break
                frame = frame.f_back
        return object.__getattribute__(self, key)

    def __setattr__(self, key, value):
        object.__setattr__(self, key, value)
        for l in self.__listeners:
            l.update()