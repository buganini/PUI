from PySide6.QtWidgets import QSizePolicy, QLayout

from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .dialog import *
from .divider import *
from .image import *
from .label import *
from .layout import *
from .modal import *
from .matplotlib import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .splitter import *
from .table import *
from .tab import *
from .text import *
from .textfield import *
from .tree import *
from .window import *
from .mdi import *
from .toolbar import *

PUIView = QtPUIView

def PUI(func):
    """
    PUI.PySide6.PUI triggers update() by signal/slot
    """
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(QtPUIView):
            pui_virtual = True
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper

PUI_BACKEND = "PySide6"
