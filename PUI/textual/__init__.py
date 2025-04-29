from .application import *
from .button import *
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
from .. import NotImplementedNode

PUIView = TPUIView

class DummyWidget(TBase):
    pui_supported = False
    def __init__(self, *args, **kwrgas):
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.Label("Not Implemented")



Canvas = DummyWidget
Combobox = DummyWidget
ComboboxItem = DummyWidget
Divider = lambda: None

PUI_BACKEND = "textual"
