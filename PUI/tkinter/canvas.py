from .. import *
from .base import *
class TkCanvas(TkBaseWidget):
    def __init__(self, size=None, **kwargs):
        super().__init__(**kwargs)
        self.size = size

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            import tkinter as tk
            self.ui = tk.Canvas(self.parent.ui, **self.kwargs)
        self.ui.delete("all")
        return self.ui

class TkCanvasText(PUINode):
    def __init__(self, x, y, text):
        super().__init__()
        self.x = x
        self.y = y
        self.text = text

    def update(self, prev):
        self.parent.ui.create_text(self.x, self.y, text=self.text)

class TkCanvasLine(PUINode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def update(self, prev):
        self.parent.ui.create_line(*self.args, **self.kwargs)