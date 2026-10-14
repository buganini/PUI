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
from .views import *

from .config import *

from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.formatters import HtmlFormatter

import inspect

# reloadium: after_reload
def after_reload(actions):
    PUIView.reload()

flags = {
    "PySide6": "Q",
    "flet": "F",
    "tkinter": "T",
    "textual": "X",
    "wx": "W",
    "web": "B"
}
pages = [
    ("QFTXWB", "Vbox", VBoxExample),
    ("QFTXWB", "HBox", HBoxExample),
    ("QF", "Stack", StackExample),
    ("QTWB", "Grid", GridExample),
    ("QFTXWB", "Label", LabelExample),
    ("QFTXW", "Text", TextExample),
    ("QFTXWB", "Button", ButtonExample),
    ("QFTXWB", "Checkbox", CheckboxExample),
    ("QFTXWB", "RadioButton", RadioButtonExample),
    ("QFTWB", "Combobox", ComboboxExample),
    ("QFTXWB", "ProgressBar", ProgressBarExample),
    ("QFTXW", "TimelineView", TimelineViewExample),
    ("QFTXWB", "TextField", TextFieldExample),
    ("QFTXWB", "Scroll", ScrollExample),
    ("QFTW", "Canvas", CanvasExample),
    ("QW", "DrawShapely", DrawShapelyExample),
    ("Q", "Matplotlib", MatplotlibCanvasExample),
    ("QFW", "Image", ImageExample),
    ("QFTXWB", "Tab", TabExample),
    ("QTXWB", "Views", ViewsExample),
    ("QFTXW", "Table", TableExample),
    ("QFTXW", "Table(Adapter)", TableAdapterExample),
    ("QW", "Tree", TreeExample),
    ("QW", "Tree(Adapter)", TreeAdapterExample),
    ("QFTXWB", "State Binding", BindingExample),
    ("Q", "WidgetWrapper", WidgetExample),
    ("Q", "Drop", DropExample),
    ("Q", "MDI", MdiExample),
    ("QW", "Splitter", SplitterExample),
    ("Q", "Modal", ModalExample),
    ("QTW", "Dialog", DialogExample),
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
                        code = inspect.getsource(inspect.unwrap(state.page[2]))
                        if Html.pui_supported:
                            formatter = HtmlFormatter(style="monokai", noclasses=True)
                            highlighted_code = highlight(code, Python3Lexer(), formatter)
                            Html(
                                f'<body bgcolor="#272822" text="#f8f8f2">{highlighted_code}</body>'
                            ).layout(padding=10).style(bgColor=0x272822, color=0xF8F8F2)
                        else:
                            Text(code).style(bgColor=0x272822, color=0xF8F8F2)

                with VBox().layout(weight=1).id("result").debug():
                    Label("Result")
                    if flags[PUI_BACKEND] in state.page[0]:
                        state.page[2]()
                    else:
                        Label("Not Supported for this backend")

    def select(self, e, page):
        print("select", page[1])
        state.page = page

