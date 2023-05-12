from .. import *
from .base import *
import itertools
class TkCanvas(TkBaseWidget):
    terminal = True
    def __init__(self, painter, *args, size=None, bgColor=None):
        super().__init__()
        self.painter = painter
        self.args = args
        self.size = size
        self.bgColor = bgColor

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = tk.Canvas(self.parent.ui, **self.kwargs)
        self.ui.delete("all")

        if self.bgColor:
            self.ui.config(bg=f"#{self.bgColor:06X}")

        self.painter(self, *self.args)

    def drawText(self, x, y, text):
        self.ui.create_text(x, y, text=text)

    def drawLine(self, x1, y1, x2, y2, color=None, width=None):
        params = {}
        if not color is None:
            params["fill"] = f"#{color:06X}"
        if not width is None:
            params["width"] = width
        self.ui.create_line(x1, y1, x2, y2, **params)

    def drawPolyline(self, coords, color=None, width=None):
        params = {}
        if not color is None:
            params["fill"] = f"#{color:06X}"
        if not width is None:
            params["width"] = width
        self.ui.create_line(*itertools.chain(*coords), **params)