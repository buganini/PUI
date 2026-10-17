from typing import Type
import sys
from rich.console import Console
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator
from textual.driver import Driver
from .. import *
from .base import *
from textual.app import App, CSSPathType, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Checkbox, Input, RadioButton, Tabs

class PUITextualApp(App):

    def __init__(self, puiview, driver_class: Type[Driver] = None, css_path: CSSPathType = None, watch_css: bool = False):
        super().__init__(driver_class, css_path, watch_css)
        self.puiview = puiview
        # Capture the launch stream before Textual redirects stdout during run().
        self._title_console = Console(file=sys.stdout)
        if puiview.title:
            self.title = puiview.title

    def on_mount(self) -> None:
        if self.puiview.title and not self.is_headless:
            title = ''.join(character for character in self.puiview.title if character.isprintable())
            self._title_console.set_window_title(title)
        self.puiview.redraw()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.button.puinode.get_node()._clicked()

    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        event.radio_button.puinode.get_node()._changed(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.puinode.get_node()._tchanged(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.puinode.get_node()._tsubmitted(event.value)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.checkbox.puinode.get_node()._changed(event.value)

    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        event.tabs.puinode.get_node()._tab_activated(event)

    def compose(self) -> ComposeResult:
        yield Vertical(id="frame")

class Application(PUIView):
    def __init__(self, *, title=''):
        super().__init__()
        self.title = title
        self.ui = PUITextualApp(self)

    def addChild(self, idx, child):
        if idx>0:
            raise RuntimeError("Textual backend only support single window")
        self.ui.query_one("#frame").mount(child.outer)

    def redraw(self):
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self.ui.call_next(self._redraw)

    def _redraw(self):
        with self.ui.batch_update():
            self.sync()
        self.updating = False

    def run(self):
        # self.redraw() # need to be after on_mount
        self.start()

    def start(self, *, landlock=None):
        from .._landlock import apply
        apply(landlock)
        self.ui.run()


def PUIApp(func):
    """Deprecated: subclass Application and implement content() instead."""
    _warn_deprecated_decorator('PUIApp', 'Application')
    @_wraps(func)
    def func_wrapper(*args, **kwargs):
        class PUIAppWrapper(Application):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIAppWrapper(func.__name__)
        return ret

    return func_wrapper
