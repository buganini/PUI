from .. import *
from .base import *
import flet as ft

class FElevatedButton(FBase):
    def __init__(self, text, callback=None, **kwargs):
        super().__init__(**kwargs)
        self.text = text
        self.callback = callback
        self.kwargs = kwargs

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = ft.ElevatedButton(text=self.text, on_click=self.on_click, **self.kwargs)

    def on_click(self, *args):
        self.callback()