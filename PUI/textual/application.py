from typing import Type
from textual.driver import Driver
from .. import *
from .base import *
from textual.app import App, CSSPathType, ComposeResult
from textual.reactive import reactive
from textual.widgets import Button

class PUIApp(App):

    def __init__(self, driver_class: Type[Driver] | None = None, css_path: CSSPathType | None = None, watch_css: bool = False):
        super().__init__(driver_class, css_path, watch_css)
        self.subs = []

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.button.puinode._clicked()

    def compose(self) -> ComposeResult:
        for c in self.subs:
            yield c

class TApplication(PUIView):
    def __init__(self):
        super().__init__()
        self.ui = PUIApp()

    def addChild(self, idx, child):
        if idx>0:
            raise RuntimeError("Textual port only support single window")
        self.ui.subs.insert(idx, child.ui)

    def start(self):
        self.ui.run()
