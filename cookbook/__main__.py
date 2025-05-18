import sys
sys.path.append("..")

from .vbox import *
from .hbox import *
from .stack import *
from .grid import *
from .label import *
from .text import *
from .button import *
from .checkbox import *
from .drop import *
from .radiobutton import *
from .combobox import *
from .modal import *
from .dialog import *
from .progressbar import *
from .table import *
from .table_adapter import *
from .tree import *
from .tree_adapter import *
from .timeline import *
from .textfield import *
from .scroll import *
from .canvas import *
from .drawshapely import *
from .matplotlib import *
from .image import *
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
    ("Q", "Stack", StackExample),
    ("QW", "Grid", GridExample),
    ("QFTXW", "Label", LabelExample),
    ("QFTXW", "Text", TextExample),
    ("QFTXW", "Button", ButtonExample),
    ("QFTXW", "Checkbox", CheckboxExample),
    ("QFTXW", "RadioButton", RadioButtonExample),
    ("QW", "Combobox", ComboboxExample),
    ("QFTXW", "ProgressBar", ProgressBarExample),
    ("QFTX", "TimelineView", TimelineViewExample),
    ("QFTXW", "TextField", TextFieldExample),
    ("QFTXW", "Scroll", ScrollExample),
    ("QFTW", "Canvas", CanvasExample),
    ("QW", "DrawShapely", DrawShapelyExample),
    ("Q", "Matplotlib", MatplotlibCanvasExample),
    ("Q", "Image", ImageExample),
    ("QFTX", "Tab", TabExample),
    ("Q", "Table", TableExample),
    ("Q", "Table(Adapter)", TableAdapterExample),
    ("Q", "Tree", TreeExample),
    ("Q", "Tree(Adapter)", TreeAdapterExample),
    ("QFTX", "State Binding", BindingExample),
    ("Q", "WidgetWrapper", WidgetExample),
    ("Q", "Drop", DropExample),
    ("Q", "MDI", MdiExample),
    ("Q", "Splitter", SplitterExample),
    ("Q", "Modal", ModalExample),
    ("QW", "Dialog", DialogExample),
]

state = State()
state.page = pages[0]

class Cookbook(Application):
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

            with HBox().debug():
                with VBox().id("menu-container").debug():
                    Label("Example")
                    with Scroll().layout(weight=1).id("menu-scroller").debug():
                        with VBox().id("menu-list").debug():
                            for p in pages:
                                Label(p[1]).click(self.select, p)
                            Spacer()

                with VBox().layout(weight=1).id("code").debug():
                    Label("Code")
                    with Scroll().layout(weight=1):
                        code = inspect.getsource(extract_wrapped(state.page[2]))
                        if Html.pui_supported:
                            formatter = HtmlFormatter()
                            formatter.noclasses = True
                            formatter.nobackground = True
                            highlighted_code = highlight(code, Python3Lexer(), formatter)
                            Html(highlighted_code).layout(padding=10).qt(StyleSheet={"background":"#0a0c0d"})
                        else:
                            Text(code)

                with VBox().layout(weight=1).id("result").debug():
                    Label("Result")
                    if flags[PUI_BACKEND] in state.page[0]:
                        state.page[2]()
                    else:
                        Label("Not Supported for this backend")

    def select(self, e, page):
        print("select", page[1])
        state.page = page

root = Cookbook()
root.run()
