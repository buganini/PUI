import sys
sys.path.append("..")

from PUI.PySide6 import *
from .label import *
from .vbox import *
from .hbox import *
from .timeline import *
from .textfield import *

from PySide6.QtGui import QSyntaxHighlighter

from pygments import highlight
from pygments.lexers import Python3Lexer
from pygments.style import Style
from pygments.formatters import HtmlFormatter

import inspect
from types import FunctionType

def extract_wrapped(decorated):
    closure = (c.cell_contents for c in decorated.__closure__)
    return next((c for c in closure if isinstance(c, FunctionType)), None)


pages = [
    ("Label", LabelExample),
    ("Vbox", VBoxExample),
    ("HBox", HBoxExample),
    ("TimelineView", TimelineViewExample),
    ("TextField (Data Binding)", TextFieldExample),
]

state = State()
state.page = pages[0]

class QtExample(QtApplication):
    def content(self):
        with Window(title="PUI Cookbook", maximize=True):
            with HBox():
                with VBox():
                    Label("Example")
                    with Scroll():
                        with VBox():
                            for p in pages:
                                Label(p[0]).click(self.select, p)
                            Spacer()

                with VBox().layout(weight=1):
                    Label("Code")
                    with Scroll():
                        code = inspect.getsource(extract_wrapped(state.page[1]))
                        formatter = HtmlFormatter()
                        formatter.noclasses = True
                        formatter.nobackground = True
                        highlighted_code = highlight(code, Python3Lexer(), formatter)
                        Text(highlighted_code).layout(padding=10).qt(StyleSheet="background:#0a0c0d")

                with VBox().layout(weight=1):
                    Label("Result")
                    with Scroll():
                        state.page[1]()

    def select(self, page):
        print("select", page[0])
        state.page = page

from PySide6 import QtWidgets
root = QtExample()
root.run()
