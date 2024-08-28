from .. import *
from .base import *
import itertools
class Canvas(TkBaseWidget):
    pui_terminal = True
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

    def drawText(self, x, y, text, w=None, h=None, rotate=0, anchor=Anchor.LEFT_TOP):
        if rotate !=0:
            print("drawText: rotate not implemented")
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

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        print("drawPolygon not implemented")

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        print("drawRect not implemented")

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        print("drawEllipse not implemented")
