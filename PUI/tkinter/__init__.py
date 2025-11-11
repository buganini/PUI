from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .tab import *
from .text import *
from .textfield import *
from .window import *

PUIView = TPUIView

def PUI(func):
    """
    PUI.tkinter.PUI triggers update() by .after()
    """
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(TPUIView):
            pui_virtual = True
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper
class DummyWidget(PUINode):
    pui_supported = False
    def __init__(self, *args, **kwargs):
        super().__init__()

Combobox = DummyWidget
ComboboxItem = DummyWidget
Divider = DummyWidget

PUI_BACKEND = "tkinter"
