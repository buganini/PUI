from .application import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from .button import *
from .canvas import *
from .checkbox import *
from .combobox import *
from .dialog import *
from .divider import *
from .label import *
from .image import *
from .tab import *
from .views import *
from .table import *
from .tree import *
from .layout import *
from .menu import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .splitter import *
from .text import *
from .textfield import *
from .textedit import *
from .window import *

PUIView = WxPUIView

def PUI(func):
    """Deprecated: subclass PUIView to keep redraws on the wx GUI queue."""
    _warn_deprecated_decorator('PUI', 'PUIView')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(WxPUIView):
            def __init__(self):
                self.name = func.__name__
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        return PUIViewWrapper()
    return func_wrapper

PUI_BACKEND = "wx"

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
from ..state_refs import noop_publish as state_ref_publish

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight
