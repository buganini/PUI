from .application import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .image import *
from .divider import *
from .label import *
from .layout import *
from .splitter import Splitter
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .tab import *
from .table import *
from .text import *
from .textfield import *
from .textedit import *
from .window import *
from .. import NotImplementedNode

Combobox = ComboBox
ComboboxItem = ComboBoxItem

PUIView = FView

def PUI(func):
    """Deprecated: subclass PUIView and implement content() instead."""
    _warn_deprecated_decorator('PUI', 'PUIView')
    @_wraps(func)
    def wrapper(*args, **kwargs):
        class View(FView):
            def __init__(self):
                self.name = func.__name__
                super().__init__()
            def content(self):
                return func(*args, **kwargs)
        return View()
    return wrapper

PUI_BACKEND = "flet"

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
from ..state_refs import noop_publish as state_ref_publish

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight

from .._matplotlib import MatplotlibMixin as _MatplotlibMixin
class MatplotlibCanvas(_MatplotlibMixin, Canvas):
    pass
