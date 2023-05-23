__version__ = "0.2.1"

from .node import *
from .view import *
from .state import *
from .timeline import *
from .decorator import *

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

    def weight(self, *args):
        return self