"""Browser-local Python backend; bootstrap in a dedicated Pyodide module worker."""
from .. import State, PUIEvent, Anchor, MouseButton, KeyModifier
from ..interfaces import BaseTableAdapter, BaseTreeAdapter
from .._browser.widgets import (PUIView, Window, VBox, HBox, Label, Button,
    TextField, MaskedField, Text, Spacer, Divider, Scroll, Html, MarkDown,
    Canvas, Image, Grid, Stack, Checkbox, RadioButton, ComboBox,
    ComboBoxItem, Combobox, ComboboxItem, ProgressBar, Tabs,
    Tab, Views, Table, TableNode, Tree, Splitter, Dialog, Confirm, Prompt,
    MatplotlibCanvas)
from .application import Application, TimelineView
from .images import ImageResource

PUI_BACKEND = 'pyodide'
