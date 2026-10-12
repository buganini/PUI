from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .image import *
from .divider import *
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .tab import *
from .table import *
from .text import *
from .textfield import *
from .window import *
from .. import NotImplementedNode

Combobox = ComboBox
ComboboxItem = ComboBoxItem

PUIView = FView

def PUI(func):
    def wrapper(*args, **kwargs):
        class View(FView):
            def __init__(self):
                self.name = func.__name__
                super().__init__()
            def content(self):
                return func(*args, **kwargs)
        return View()
    return wrapper

PUI_BACKEND = "flet"
