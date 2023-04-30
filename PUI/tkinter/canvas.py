from .. import *
from .base import *
class TkCanvas(TkBaseWidget):
    terminal = True
    def __init__(self, size=None, **kwargs):
        super().__init__(**kwargs)
        self.size = size

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = tk.Canvas(self.parent.ui, **self.kwargs)
        self.ui.delete("all")

        for c in self.children:
            c.update(None)


class TkCanvasText(PUINode):
    def __init__(self, x, y, text):
        super().__init__()
        self.x = x
        self.y = y
        self.text = text

    def update(self, prev):
        self.parent.ui.create_text(self.x, self.y, text=self.text)

class TkCanvasLine(PUINode):
    def __init__(self, x1, y1, x2, y2, color=None, width=None):
        super().__init__()
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.width = width

    def update(self, prev):
        params = {}
        if not self.color is None:
            params["fill"] = f"#{self.color:06X}"
        if not self.width is None:
            params["width"] = self.width
        self.parent.ui.create_line(self.x1, self.y1, self.x2, self.y2, **params)
class TkCanvasPolyline(PUINode):
    def __init__(self, coords, color=None, width=None):
        super().__init__()
        self.coords = coords
        self.color = color
        self.width = width

    def update(self, prev):
        params = {}
        if not self.color is None:
            params["fill"] = f"#{self.color:06X}"
        if not self.width is None:
            params["width"] = self.width
        self.parent.ui.create_line(*self.coords, **params)