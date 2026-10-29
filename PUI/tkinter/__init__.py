from .application import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from .button import *
from .canvas import *
from .checkbox import *
from .dialog import *
from .divider import *
from .combobox import *
from .label import *
from .layout import *
from .splitter import Splitter
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .tab import *
from .table import Table, TableNode
from .views import *
from .text import *
from .textfield import *
from .textedit import *
from .window import *

PUIView = TPUIView

def PUI(func):
    """
    Deprecated: subclass PUIView and implement content() instead.

    PUI.tkinter.PUI triggers update() by .after().
    """
    _warn_deprecated_decorator('PUI', 'PUIView')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(TPUIView):
            pui_virtual = True
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIViewWrapper(func.__name__)
        return ret

    return func_wrapper
class DummyWidget(PUINode):
    pui_supported = False
    def __init__(self, *args, **kwargs):
        super().__init__()

Combobox = ComboBox
ComboboxItem = ComboBoxItem

PUI_BACKEND = "tkinter"

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
from ..state_refs import noop_publish as state_ref_publish

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight

from .matplotlib import MatplotlibCanvas

from .modal import Modal

from .menu import MenuBar, Menu, MenuAction

from .tree import Tree, TreeNode

from .._url import OpenURL
