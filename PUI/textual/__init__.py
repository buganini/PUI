from .application import *
from .button import *
from .checkbox import *
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .text import *
from .textfield import *
from .window import *
from .. import NotImplementedNode

class DummyWidget(TBase):
    supported = False
    def __init__(self, *args, **kwrgas):
        super().__init__()

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = widgets.Label("Not Implemented")


Application = TApplication
Window = TWindow
HBox = THorizontal
VBox = TVertical
Label = TLabel
Button = TButton
Checkbox = TCheckbox
RadioButton = TRadioButton
Canvas = DummyWidget
TextField = TInput
ProgressBar = TProgressBar
Scroll = TScroll
Spacer = TSpacer
Text = TText
Html = DummyWidget
MarkDown = TLabel
Combobox = DummyWidget
ComboboxItem = DummyWidget

PUI_BACKEND = "textual"
