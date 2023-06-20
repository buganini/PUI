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
class DummyWidget(PUINode):
    supported = False
    def __init__(self, *args, **kwargs):
        super().__init__()

Combobox = DummyWidget
ComboboxItem = DummyWidget

PUI_BACKEND = "tkinter"
