from .. import *
from .base import *

from PySide6 import QtWidgets, QtGui
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import QPoint

class PUIQtCanvas(QtWidgets.QWidget):
    def __init__(self, node, width=None, height=None):
        self.node = node
        self.width = width
        self.height = height
        super().__init__()

    def minimumSizeHint(self):
        return QtCore.QSize(self.width, self.height)

    def paintEvent(self, event):
        while self.node.retired_by:
            self.node = self.node.retired_by
        self.node.qpainter = QPainter()
        self.node.qpainter.begin(self)

        if not self.node.style_bgcolor is None:
            bgBrush = QtGui.QBrush()
            bgBrush.setColor(QtGui.QColor(self.node.style_bgcolor))
            bgBrush.setStyle(QtCore.Qt.SolidPattern)
            rect = QtCore.QRect(0, 0, self.width or self.geometry().width(), self.height or self.geometry().height())
            self.node.qpainter.fillRect(rect, bgBrush)

        self.node.painter(self.node, *self.node.args)

        self.node.qpainter.end()
        self.node.qpainter = None

class Canvas(QtBaseWidget):
    def __init__(self, painter, *args):
        super().__init__()
        self.ui = None
        self.painter = painter
        self.args = args

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.puinode = self
            self.ui.width = self.layout_width or 0
            self.ui.height = self.layout_height or 0
        else:
            self.ui = PUIQtCanvas(self, self.layout_width or 0, self.layout_height or 0)
        self.ui.update()
        super().update(prev)

    def drawText(self, x, y, text):
        self.qpainter.drawText(QPoint(int(x), int(y)), text)

    def drawLine(self, x1, y1, x2, y2, color=None, width=None):
        pen = self.qpainter.pen()
        orig_color = pen.color()
        orig_width = pen.width()
        if not color is None:
            pen.setColor(QColor(color))
        if not width is None:
            pen.setWidth(width)
        self.qpainter.setPen(pen)
        self.qpainter.drawLine(x1, y1, x2, y2)
        pen.setColor(orig_color)
        pen.setWidth(orig_width)
        self.qpainter.setPen(pen)

    def drawPolyline(self, coords, color=None, width=None):
        pen = self.qpainter.pen()
        orig_color = pen.color()
        orig_width = pen.width()
        if not color is None:
            pen.setColor(QColor(color))
        if not width is None:
            pen.setWidth(width)
        self.qpainter.setPen(pen)
        self.qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in coords])
        pen.setColor(orig_color)
        pen.setWidth(orig_width)
        self.qpainter.setPen(pen)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2-x1)
        h = abs(y2-y1)

        if fill is not None:
            self.qpainter.fillRect(x, y, w, h, QColor(fill))

        if stroke is not None:
            pen = self.qpainter.pen()
            orig_color = pen.color()
            orig_width = pen.width()

            pen.setColor(QColor(stroke))
            pen.setWidth(width)
            self.qpainter.setPen(pen)
            self.qpainter.drawRect(x, y, w, h)

            pen.setColor(orig_color)
            pen.setWidth(orig_width)
            self.qpainter.setPen(pen)
