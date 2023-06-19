from .. import *
from .base import *
import itertools
class Canvas(TkBaseWidget):
    terminal = True
    def __init__(self, painter, *args):
        super().__init__()
        self.painter = painter
        self.args = args

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Canvas(self.tkparent.inner)
        self.ui.delete("all")

        self.painter(self, *self.args)
        super().update(prev)

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