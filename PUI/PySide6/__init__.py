import PySide6
from PySide6.QtWidgets import QSizePolicy, QLayout

from .application import *
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .splitter import *
from .text import *
from .textfield import *
from .window import *
from .mdi import *

Application = QtApplication
Window = QtWindow
HBox = QtHBox
VBox = QtVBox
Label = QtLabel
Button = QtButton
Checkbox = QtCheckbox
RadioButton = QtRadioButton
Canvas = QtCanvas
TextField = QtLineEdit
ProgressBar = QtProgressBar
Scroll = QtScrollArea
Spacer = QtSpacerItem
Text = QtText
Html = QtHtml
MarkDown = QtMarkDown
Combobox = QtComboBox
ComboboxItem = QtComboBoxItem

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
                return func(*args)

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper

PUI = QtPUI

PUI_BACKEND = "PySide6"
