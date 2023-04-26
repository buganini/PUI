from .. import *
from .base import *

from PyQt5 import QtWidgets
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtCore import QPoint

class PUIQtCanvas(QtWidgets.QWidget):
    def __init__(self, puinode):
        self.puinode = puinode
        super().__init__()

    def paintEvent(self, event):
        qpainter = QPainter()
        qpainter.begin(self)

        for c in self.puinode.children:
            c.draw(qpainter)

        qpainter.end()

class QtCanvas(QtBaseWidget):
    def __init__(self, size=None, **kwargs):
        super().__init__(**kwargs)
        self.size = size

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.puinode = self
        else:
            self.ui = PUIQtCanvas(self)
        x = 0
        y = 0
        w = 0
        h = 0
        if not self.size is None:
            w, h = self.size
        self.ui.setGeometry(x, y, w, h)
        self.ui.update()

class QtCanvasText(PUINode):
    def __init__(self, x, y, text):
        super().__init__()
        self.x = x
        self.y = y
        self.text = text

    def update(self, prev):
        pass

    def draw(self, qpainter):
        qpainter.drawText(QPoint(int(self.x), int(self.y)), self.text)

class QtCanvasLine(PUINode):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.args = args
        self.kwargs = kwargs

    def update(self, prev):
        pass

    def draw(self, qpainter):
        qpainter.drawLine(*self.args)