"""Browser-local Python backend; bootstrap in a dedicated Pyodide module worker."""
from .. import State, PUIEvent, Anchor, Side, MouseButton, KeyModifier
from ..interfaces import BaseTableAdapter, BaseTreeAdapter
from .._browser.widgets import (PUIView, Window, VBox, HBox, HVBox, VHBox, Label, Button,
    TextField, MaskedField, Text, Spacer, Divider, Scroll, Html, MarkDown,
    Canvas, Image, Grid, Stack, Checkbox, RadioButton, ComboBox,
    ComboBoxItem, Combobox, ComboboxItem, ProgressBar, Tabs,
    Tab, Views, Table, TableNode, Tree, Splitter, Dialog, Confirm, Prompt,
    MatplotlibCanvas)
from .application import Application, TimelineView
from .images import ImageResource

PUI_BACKEND = 'pyodide'

# Public lookup into the shared internal registry.
from ..refs import ref

# Replace this callback to publish named State values outside the UI.
from ..state_refs import noop_publish as state_ref_publish

from ..options import load_environment as _load_options_environment
_load_options_environment()

from ..common import FontWeight
