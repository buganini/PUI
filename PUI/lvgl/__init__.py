from .application import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from .button import *
from .checkbox import *
from .divider import *
from .image import Image
from .label import *
from .layout import *
from .progressbar import *
from .scroll import *
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
    pui_supported = False
    def __init__(self, *args, **kwargs):
        super().__init__()

Splitter = DummyWidget
TabView = DummyWidget
TabPane = DummyWidget
Canvas = DummyWidget
Text = DummyWidget
Html = DummyWidget
Markdown = DummyWidget
ComboBox = DummyWidget
FontPicker = DummyWidget
Table = DummyWidget
Tree = DummyWidget
MenuBar = DummyWidget
Menu = DummyWidget
MenuItem = DummyWidget
Modal = DummyWidget
Toast = DummyWidget
Radio = DummyWidget
RadioButton = DummyWidget
PasswordField = DummyWidget
TextEditor = DummyWidget
NativeWidget = DummyWidget
NativeLayout = DummyWidget
Tabs = DummyWidget
Tab = DummyWidget
ComboBoxItem = DummyWidget

PUI_BACKEND = "lvgl"

from ..refs import ref
from ..state_refs import noop_publish as state_ref_publish
from ..options import load_environment as _load_options_environment
_load_options_environment()
from ..common import FontWeight
from .._url import OpenURL
