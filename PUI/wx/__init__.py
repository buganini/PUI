from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .dialog import *
from .divider import *
from .label import *
from .image import *
from .tab import *
from .views import *
from .table import *
from .tree import *
from .layout import *
from .menu import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .splitter import *
from .text import *
from .textfield import *
from .window import *

PUIView = WxPUIView

def PUI(func):
    """Build a reactive view whose redraws run on the wx GUI queue."""
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(WxPUIView):
            def __init__(self):
                self.name = func.__name__
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        return PUIViewWrapper()
    return func_wrapper

PUI_BACKEND = "wx"
