from typing import Type
from textual.driver import Driver
from .. import *
from .base import *
from textual.app import App, CSSPathType, ComposeResult
from textual.containers import Vertical
from textual.widgets import Button, Checkbox, Input, RadioButton

class PUIApp(App):

    def __init__(self, puiview, driver_class: Type[Driver] | None = None, css_path: CSSPathType | None = None, watch_css: bool = False):
        super().__init__(driver_class, css_path, watch_css)
        self.puiview = puiview

    def on_mount(self) -> None:
        self.puiview.redraw()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.button.puinode._clicked()

    def on_radio_button_changed(self, event: RadioButton.Changed) -> None:
        event.radio_button.puinode._changed(event.value)

    def on_input_changed(self, event: Input.Changed) -> None:
        event.input.puinode._changed(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.input.puinode._submitted(event.value)

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        event.checkbox.puinode._changed(event.value)

    def compose(self) -> ComposeResult:
        yield Vertical(id="frame")

class TApplication(PUIView):
    def __init__(self):
        super().__init__()
        self.ui = PUIApp(self)

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
            self.update(redraw=True)
        self.updating = False

    def run(self):
        # self.redraw() # need to be after on_mount
        self.start()

    def start(self):
        self.ui.run()
