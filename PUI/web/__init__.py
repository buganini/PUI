"""Server-rendered Web backend."""
from .. import State, PUIEvent, Anchor, Side, MouseButton, KeyModifier, TimelineView
from ..interfaces import BaseTableAdapter, BaseTreeAdapter
from .images import ImageResource
from .widgets import (Application, PUIView, Window, VBox, HBox, HVBox, VHBox, Label, Button,
                      TextField, MaskedField, Text, Spacer, Divider, Scroll, Html, MarkDown,
                      Canvas, Image, Grid, Stack, Checkbox, RadioButton, ComboBox,
                      ComboBoxItem, Combobox, ComboboxItem, ProgressBar, Tabs,
                      Tab, Views, Table, TableNode, Tree, Splitter, Dialog, Confirm, Prompt,
                      MatplotlibCanvas)

PUI_BACKEND = 'web'

# Public lookup into the shared internal registry.
from ..refs import ref


def state_ref_publish(name, value):
    """Collect a named State value for batched URL synchronization."""
    from ..view import find_puiview
    view = find_puiview()
    view.runtime.state_refs.publish(view, name, value)
