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

class DummyWidget(TBase):
    supported = False
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

PUI_BACKEND = "textual"
