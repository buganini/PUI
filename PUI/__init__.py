__version__ = "0.6.1"

from .node import *
from .view import *
from .state import *
from .timeline import *
from .decorator import *
from .common import *

class Prop():
    def __init__(self, value=None):
        self.value = value

    def set(self, value):
        changed = (self.value != value)
        self.value = value
        return changed

class NotImplementedNode():
    def __init__(self, *args, **kwargs):
        print("Not Implemented")
        import traceback
        import inspect
        traceback.print_stack(inspect.currentframe().f_back, 1)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def layout(self, *args, **kwargs):
        return self

    def style(self, *args, **kwargs):
        return self