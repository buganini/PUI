"""Browser-local Python backend; bootstrap in a dedicated Pyodide module worker."""
from .. import State, PUIEvent, Anchor, Side, MouseButton, KeyModifier
from ..interfaces import BaseTableAdapter, BaseTreeAdapter
from .._browser.widgets import (PUIView, Window, VBox, HBox, HVBox, VHBox, Label, Button,
    TextField, TextEdit, MaskedField, Text, Spacer, Divider, Scroll, Html, MarkDown,
    Canvas, Image, Grid, Stack, Checkbox, RadioButton, ComboBox,
    ComboBoxItem, Combobox, ComboboxItem, ProgressBar, Tabs,
    Tab, Views, Modal, Table, TableNode, Tree, TreeNode, Splitter, Dialog, Confirm, Prompt,
    MatplotlibCanvas, MenuBar, Menu, MenuAction)
from .application import Application, TimelineView
from .images import ImageResource
from .dialog import SaveFile, Information, Warning, Critical, Confirm, Prompt, OpenDirectory, OpenFile, OpenFiles

PUI_BACKEND = 'pyodide'

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
def state_ref_publish(name, value):
    """Collect a named State value for batched URL synchronization."""
    from ..view import find_puiview
    view = find_puiview()
    view.runtime.state_refs.publish(view, name, value)

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight

from ..color import Color

from .._browser.url import OpenURL
