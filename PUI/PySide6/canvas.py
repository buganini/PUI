from .. import *
from .base import *

from PySide6 import QtWidgets, QtGui
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import QPoint

class PUIQtCanvas(QtWidgets.QWidget):
    def __init__(self, puinode, width=None, height=None):
        self.puinode = puinode
        self.width = width
        self.height = height
        super().__init__()

    def minimumSizeHint(self):
        return QtCore.QSize(self.width, self.height)

    def paintEvent(self, event):
        qpainter = QPainter()
        qpainter.begin(self)

        if not self.puinode.bgColor is None:
            bgBrush = QtGui.QBrush()
            bgBrush.setColor(QtGui.QColor(self.puinode.bgColor))
            bgBrush.setStyle(QtCore.Qt.SolidPattern)
            rect = QtCore.QRect(0, 0, qpainter.device().width, qpainter.device().height)
            qpainter.fillRect(rect, bgBrush)

        for c in self.puinode.children:
            c.draw(qpainter)

        qpainter.end()

class QtCanvas(QtBaseWidget):
    def __init__(self, bgColor=None):
        super().__init__()
        self.ui = None
        self.bgColor = bgColor

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.puinode = self
        else:
            self.ui = PUIQtCanvas(self, self.layout_width or 0, self.layout_height or 0)
        self.ui.update()
        super().update(prev)

class QtCanvasText(PUINode):
    def __init__(self, x, y, text):
        super().__init__()
        self.x = x
        self.y = y
        self.text = text

    def draw(self, qpainter):
        qpainter.drawText(QPoint(int(self.x), int(self.y)), self.text)

class QtCanvasLine(PUINode):
    def __init__(self, x1, y1, x2, y2, color=None, width=None):
        super().__init__()
        self.x1 = x1
        self.y1 = y1
        self.x2 = x2
        self.y2 = y2
        self.color = color
        self.width = width

    def draw(self, qpainter):
        pen = qpainter.pen()
        color = pen.color()
        width = pen.width()
        if not self.color is None:
            pen.setColor(QColor(self.color))
        if not self.width is None:
            pen.setWidth(self.width)
        qpainter.setPen(pen)
        qpainter.drawLine(self.x1, self.y1, self.x2, self.y2)
        pen.setColor(color)
        pen.setWidth(width)
        qpainter.setPen(pen)

class QtCanvasPolyline(PUINode):
    def __init__(self, coords, color=None, width=None):
        super().__init__()
        self.coords = coords
        self.color = color
        self.width = width

    def draw(self, qpainter):
        pen = qpainter.pen()
        color = pen.color()
        width = pen.width()
        if not self.color is None:
            pen.setColor(QColor(self.color))
        if not self.width is None:
            pen.setWidth(self.width)
        qpainter.setPen(pen)
        qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in self.coords])
        pen.setColor(color)
        pen.setWidth(width)
        qpainter.setPen(pen)
