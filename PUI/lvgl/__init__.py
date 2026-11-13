from .application import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from .button import *
from .checkbox import *
from .combobox import *
from .divider import *
from .image import Image
from .label import *
from .layout import *
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .splitter import *
from .tab import *
from .text import *
from .textedit import *
from .textfield import *
from .views import *
from .window import *

PUIView = LPUIView

def PUI(func):
    """
    Deprecated: subclass PUIView and implement content() instead.
    """
    _warn_deprecated_decorator('PUI', 'PUIView')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIViewWrapper(LPUIView):
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
    """Placeholder for widgets the LVGL backend does not implement."""
    pui_supported = False
    pui_terminal = True
    def __init__(self, *args, **kwargs):
        super().__init__()

Canvas = DummyWidget
FontPicker = DummyWidget
Table = DummyWidget
Tree = DummyWidget
MenuBar = DummyWidget
Menu = DummyWidget
MenuItem = DummyWidget
MenuAction = DummyWidget
Modal = DummyWidget
Toast = DummyWidget
NativeWidget = DummyWidget
NativeLayout = DummyWidget

PUI_BACKEND = "lvgl"

from ..refs import ref
from ..state_refs import noop_publish as state_ref_publish
from ..options import load_environment as _load_options_environment
_load_options_environment()
from ..common import FontWeight
from .._url import OpenURL
