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
from .maskedfield import *
from .scroll import *
from .canvas import *
from .heavycanvas import *
from .drawshapely import *
from .matplotlib import *
from .image import *
from .tab import *
from .binding import *
from .widget import *
from .mdi import *
from .splitter import *
from .views import *
from .refs import RefsExample

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
    "web": "B",
    "pyodide": "Y"
}
pages = [
    ("QFTXWBY", "Vbox", VBoxExample),
    ("QFTXWBY", "HBox", HBoxExample),
    ("QFBY", "Stack", StackExample),
    ("QTWBY", "Grid", GridExample),
    ("QFTXWBY", "Label", LabelExample),
    ("QFTXW", "Text", TextExample),
    ("QFTXWBY", "Button", ButtonExample),
    ("QFTXWBY", "Checkbox", CheckboxExample),
    ("QFTXWBY", "RadioButton", RadioButtonExample),
    ("QFTWBY", "Combobox", ComboboxExample),
    ("QFTXWBY", "ProgressBar", ProgressBarExample),
    ("QFTXWBY", "TimelineView", TimelineViewExample),
    ("QFTXWBY", "TextField", TextFieldExample),
    ("QFTXWBY", "MaskedField", MaskedFieldExample),
    ("QFTXWBY", "Scroll", ScrollExample),
    ("QFTWBY", "Canvas", CanvasExample),
    ("QFTWBY", "HeavyCanvas", HeavyCanvasExample),
    ("QWB", "DrawShapely", DrawShapelyExample),
    ("Q", "Matplotlib", MatplotlibCanvasExample),
    ("QFWBY", "Image", ImageExample),
    ("QFTXWBY", "Tab", TabExample),
    ("QFTXWBY", "Refs", RefsExample),
    ("QTXWBY", "Views", ViewsExample),
    ("QFTXWBY", "Table", TableExample),
    ("QFTXWBY", "Table(Adapter)", TableAdapterExample),
    ("QW", "Tree", TreeExample),
    ("QW", "Tree(Adapter)", TreeAdapterExample),
    ("QFTXWBY", "State Binding", BindingExample),
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
    def __init__(self, *args, title='PUI Cookbook', **kwargs):
        super().__init__(*args, title=title, **kwargs)
        self.tkinter(theme="classic") # macOS's aqua doesn't respect background setting for some widgets

    def setup(self):
        if PUI_BACKEND == "tkinter":
            try:
                import sv_ttk
            except ModuleNotFoundError as error:
                if error.name != "sv_ttk":
                    raise
            else:
                sv_ttk.set_theme("light", root=self.ui)

    def content(self):
        with Window(maximize=True).ref('cookbook.window'):

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

