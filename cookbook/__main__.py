import sys
sys.path.append("..")

from .vbox import *
from .hbox import *
from .grid import *
from .label import *
from .text import *
from .button import *
from .checkbox import *
from .radiobutton import *
from .combobox import *
from .modal import *
from .dialog import *
from .progressbar import *
from .table import *
from .timeline import *
from .textfield import *
from .scroll import *
from .canvas import *
from .tab import *
from .binding import *
from .widget import *
from .mdi import *
from .splitter import *

from .config import *

from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.style import Style
from pygments.formatters import HtmlFormatter

import inspect
from types import FunctionType

def extract_wrapped(decorated):
    if not hasattr(decorated, "__closure__"):
        return decorated
    closure = (c.cell_contents for c in decorated.__closure__)
    return next((c for c in closure if isinstance(c, FunctionType)), None)

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()

flags = {
    "PySide6": "Q",
    "flet": "F",
    "tkinter": "T",
    "textual": "X",
    "wx": "W"
}
pages = [
    ("QFTXW", "Vbox", VBoxExample),
    ("QFTXW", "HBox", HBoxExample),
    ("QW", "Grid", GridExample),
    ("QFTXW", "Label", LabelExample),
    ("QFTXW", "Text", TextExample),
    ("QFTXW", "Button", ButtonExample),
    ("QFTX", "Checkbox", CheckboxExample),
    ("QFTX", "RadioButton", RadioButtonExample),
    ("Q", "Combobox", ComboboxExample),
    ("QFTX", "ProgressBar", ProgressBarExample),
    ("QFTX", "TimelineView", TimelineViewExample),
    ("QFTX", "TextField", TextFieldExample),
    ("QFTX", "Scroll", ScrollExample),
    ("QFT", "Canvas", CanvasExample),
    ("QFTX", "Tab", TabExample),
    ("Q", "Table", TableExample),
    ("QFTX", "State Binding", BindingExample),
    ("Q", "WidgetWrapper", WidgetExample),
    ("Q", "MDI", MdiExample),
    ("Q", "Splitter", SplitterExample),
    ("Q", "Modal", ModalExample),
    ("Q", "Dialog", DialogExample),
]

state = State()
state.page = pages[0]

class Example(Application):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tkinter(theme="classic") # macOS's aqua doesn't respect background setting for some widgets

    def content(self):
        with Window(title="PUI Cookbook", maximize=True):

            if PUI_BACKEND == "PySide6":
                with MenuBar():
                    with Menu("Menu"):
                        MenuAction("Action").trigger(print, "action")
                        MenuAction("Action2").trigger(print, "action2")
                        with Menu("Menu2"):
                            MenuAction("Action3").trigger(print, "action3")
                            MenuAction("Action4").trigger(print, "action4")
                    with Menu("Menu3"):
                            MenuAction("Action5")
                            MenuAction("Action6")

            with HBox():
                with VBox():
                    Label("Example")
                    with Scroll():
                        with VBox():
                            for p in pages:
                                Label(p[1]).click(self.select, p)
                            Spacer()

                with VBox().layout(weight=1):
                    Label("Code")
                    with Scroll():
                        code = inspect.getsource(extract_wrapped(state.page[2]))
                        if Html.supported:
                            formatter = HtmlFormatter()
                            formatter.noclasses = True
                            formatter.nobackground = True
                            highlighted_code = highlight(code, Python3Lexer(), formatter)
                            Html(highlighted_code).layout(padding=10).qt(StyleSheet={"background":"#0a0c0d"})
                        else:
                            Text(code)

                with VBox().layout(weight=1):
                    Label("Result")
                    if flags[PUI_BACKEND] in state.page[0]:
                        state.page[2]()
                    else:
                        Label("Not Supported for this backend")

    def select(self, page):
        print("select", page[1])
        state.page = page

root = Example()
root.run()
