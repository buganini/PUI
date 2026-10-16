"""Server-rendered Web backend."""
from .. import State, PUIEvent, Anchor, MouseButton, KeyModifier, TimelineView
from ..interfaces import BaseTableAdapter, BaseTreeAdapter
from .images import ImageResource
from .widgets import (Application, PUIView, Window, VBox, HBox, Label, Button,
                      TextField, MaskedField, Text, Spacer, Divider, Scroll, Html, MarkDown,
                      Canvas, Image, Grid, Stack, Checkbox, RadioButton, ComboBox,
                      ComboBoxItem, Combobox, ComboboxItem, ProgressBar, Tabs,
                      Tab, Views, Table, TableNode, Tree, Splitter, Dialog, Confirm, Prompt,
                      MatplotlibCanvas)

PUI_BACKEND = 'web'
