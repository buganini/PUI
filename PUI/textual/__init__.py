from .application import *
from .button import *
from .checkbox import *
from .combobox import *
from .divider import Divider
from .label import *
from .layout import *
from .splitter import Splitter
from .grid import Grid
from .progressbar import *
from .radiobutton import *
from .scroll import *
from .tab import *
from .table import Table, TableNode
from .text import *
from .textfield import *
from .textedit import *
from .window import *
from .views import *
from .. import NotImplementedNode

PUIView = TPUIView

class DummyWidget(TBase):
    pui_supported = False
    def __init__(self, *args, **kwrgas):
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = widgets.Label("Not Implemented")



from .._canvas import CanvasScope


class Canvas(CanvasScope, DummyWidget):
    pass

PUI_BACKEND = "textual"

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
from ..state_refs import noop_publish as state_ref_publish

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight

from .modal import Modal
