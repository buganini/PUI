import PySide6
from PySide6.QtWidgets import QSizePolicy, QLayout

from .application import *
from .button import *
from .canvas import *
from .combobox import *
from .label import *
from .layout import *
from .progressbar import *
from .scroll import *
from .text import *
from .textfield import *
from .window import *

Application = QtApplication
Window = QtWindow
HBox = QtHBox
VBox = QtVBox
Label = QtLabel
Button = QtButton
Canvas = QtCanvas
CanvasText = QtCanvasText
CanvasLine = QtCanvasLine
CanvasPolyline = QtCanvasPolyline
TextField = QtLineEdit
ProgressBar = QtProgressBar
Scroll = QtScrollArea
Spacer = QtSpacerItem
Text = QtText

def QtPUI(func):
    """
    PUI.PySide6.PUI triggers update() by signal/slot
    """
    def func_wrapper(*args):
        class PUIViewWrapper(QPUIView):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return self.__wrapped_content__()

            def __wrapped_content__(self):
                return func(*args)
        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper

PUI = QtPUI
