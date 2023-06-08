from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .text import *
from .textfield import *
from .window import *

class DummyWidget(PUINode):
    supported = False

Application = TkApplication
Window = TkWindow
HBox = TkHBox
VBox = TkVBox
Label = TkLabel
Button = TkButton
Checkbox = TkCheckbutton
RadioButton = TkRadiobutton
Canvas = TkCanvas
Text = TkLabel
TextField = TkEntry
ProgressBar = TkProgressBar
Scroll = TkScroll
Spacer = TkSpacer
Text = TkText
Html = DummyWidget
MarkDown = DummyWidget

PUI_BACKEND = "tkinter"
