import PUI as pui

from .vbox import *
from .adaptive import AdaptiveLayoutExample
from .adaptive_grid import AdaptiveGridExample
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
from .textedit import *
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
    ("QFTXWBY", "Adaptive Layout", AdaptiveLayoutExample),
    ("QFTXWBY", "Vbox", VBoxExample),
    ("QFTXWBY", "HBox", HBoxExample),
    ("QFTXWBY", "Stack", StackExample),
    ("QTXWBY", "Grid", GridExample),
    ("QTXWBY", "Adaptive Grid", AdaptiveGridExample),
    ("QFTXWBY", "Label", LabelExample),
    ("QFTXWBY", "Text", TextExample),
    ("QFTXWBY", "Button", ButtonExample),
    ("QFTXWBY", "Checkbox", CheckboxExample),
    ("QFTXWBY", "RadioButton", RadioButtonExample),
    ("QFTXWBY", "Combobox", ComboboxExample),
    ("QFTXWBY", "ProgressBar", ProgressBarExample),
    ("QFTXWBY", "TimelineView", TimelineViewExample),
    ("QFTXWBY", "TextField", TextFieldExample),
    ("QFTXWBY", "TextEdit", TextEditExample),
    ("QFTXWBY", "MaskedField", MaskedFieldExample),
    ("QFTXWBY", "Scroll", ScrollExample),
    ("QFTWBY", "Canvas", CanvasExample),
    ("QFTWBY", "HeavyCanvas", HeavyCanvasExample),
    ("QWB", "DrawShapely", DrawShapelyExample),
    ("QFWTBY", "Matplotlib", MatplotlibCanvasExample),
    ("QFWBY", "Image", ImageExample),
    ("QFTXWBY", "Tab", TabExample),
    ("QFTXWBY", "Refs", RefsExample),
    ("QTXWBY", "Views", ViewsExample),
    ("QFTXWBY", "Table", TableExample),
    ("QFTXWBY", "Table(Adapter)", TableAdapterExample),
    ("QW", "Tree", TreeExample),
    ("QW", "Tree(Adapter)", TreeAdapterExample),
    ("QFTXWBY", "State & Binding", BindingExample),
    ("Q", "WidgetWrapper", WidgetExample),
    ("QWBY", "Drop", DropExample),
    ("Q", "MDI", MdiExample),
    ("QFTXWBY", "Splitter", SplitterExample),
    ("QFTBYX", "Modal", ModalExample),
    ("QTWB", "Dialog", DialogExample),
]

class Cookbook(Application):
    def __init__(self, *args, title=f'Cookbook ({PUI_BACKEND})', **kwargs):
        super().__init__(*args, title=title, **kwargs)
        self.tkinter(theme="classic") # macOS's aqua doesn't respect background setting for some widgets

    def setup(self):
        self.state = State()
        initial_page = pui.Options.get('cookbook.page')
        self.state.page = next((p[1] for p in pages if p[1] == initial_page), pages[0][1])
        if PUI_BACKEND == "tkinter":
            try:
                import sv_ttk
            except ModuleNotFoundError as error:
                if error.name != "sv_ttk":
                    raise
            else:
                sv_ttk.set_theme("light", root=self.ui)

    def content(self):
        page_name = self.state('page').ref('cookbook.page').value
        page = next(p for p in pages if p[1] == page_name)
        with Window(size=(1024, 768)).ref('cookbook.window'):

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
                    Label(f"Cookbook ({PUI_BACKEND})")
                    with Scroll().layout(weight=1).id("menu-scroller").debug():
                        with VBox().id("menu-list").debug():
                            for p in pages:
                                weight = FontWeight.Bold if p[1] == page_name else FontWeight.Normal
                                Label(p[1]).style(fontWeight=weight).tStyle(
                                    fontWeight=weight,
                                ).click(self.select, p[1])
                            Spacer()

                with Splitter().layout(weight=1).id('example-panes'):
                    with VBox().layout(weight=1).id("code").debug():
                        Label("Code")
                        with Scroll(horizontal=None).layout(weight=1):
                            code = inspect.getsource(inspect.unwrap(page[2]))
                            if Html.pui_supported:
                                formatter = HtmlFormatter(style="monokai", noclasses=True)
                                highlighted_code = highlight(code, Python3Lexer(), formatter)
                                Html(
                                    f'<body bgcolor="#272822" text="#f8f8f2">{highlighted_code}</body>'
                                ).layout(padding=10).style(bgColor=0x272822, color=0xF8F8F2)
                            else:
                                Text(code).style(bgColor=0x272822, color=0xF8F8F2).tStyle(bgColor=0x272822, color=0xF8F8F2)

                    with VBox().layout(weight=1).id("result").debug():
                        Label("Result")
                        if flags[PUI_BACKEND] in page[0]:
                            page[2]()
                        else:
                            Label("Not Supported for this backend")

    def select(self, e, page):
        print("select", page)
        self.state.page = page

