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

    def mouseDoubleClickEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._dblclicked(e)

    def mousePressEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mousedown(e)

    def mouseReleaseEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mouseup(e)

    def mouseMoveEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mousemove(e)

    def wheelEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        e.y_delta = event.pixelDelta().y()
        e.x_delta = event.pixelDelta().x()
        e.v_delta = event.angleDelta().y()
        e.h_delta = event.angleDelta().x()
        self.node._wheel(e)

    def paintEvent(self, event):
        while self.node.retired_by:
            self.node = self.node.retired_by
        self.node.qpainter = QPainter()
        self.node.qpainter.begin(self)
        self.node.qpainter.setRenderHints(QtGui.QPainter.Antialiasing, True)

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
        self.ui.setMouseTracking(bool(self._onMouseMove))
        self.ui.update()
        super().update(prev)

    def drawText(self, x, y, text, w=None, h=None, rotate=0, anchor=Anchor.LEFT_TOP):
        if w is None:
            w = self.ui.geometry().width()
        if h is None:
            h = self.ui.geometry().height()
        self.qpainter.save()
        br = self.qpainter.boundingRect(0, 0, w, h, 0, text)
        self.qpainter.restore()

        dx = 0
        dy = 0
        if anchor.value[0]=="center":
            dx = br.width()/2
        elif anchor.value[0]=="right":
            dx = br.width()

        if anchor.value[1]=="center":
            dy = br.height()/2
        elif anchor.value[1]=="bottom":
            dy = br.height()

        self.qpainter.save()
        self.qpainter.translate(int(x+dx), int(y+dy))
        self.qpainter.rotate(rotate)
        self.qpainter.translate(int(-dx), int(-dy))

        self.qpainter.drawText(0, 0, w, h, 0, text)
        self.qpainter.restore()

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()
        if not color is None:
            pen.setColor(QColor(color))
        pen.setWidth(width)
        self.qpainter.setPen(pen)
        self.qpainter.drawLine(x1, y1, x2, y2)

        self.qpainter.restore()

    def drawPolyline(self, coords, color=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()

        if not color is None:
            pen.setColor(QColor(color))
        pen.setWidth(width)
        self.qpainter.setPen(pen)
        self.qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in coords])

        self.qpainter.restore()

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()
        if fill is not None:
            self.qpainter.setBrush(QColor(fill))
        if stroke is not None:
            pen.setColor(QColor(stroke))
            pen.setWidth(width)
            self.qpainter.setPen(pen)

        polygon = QtGui.QPolygonF()
        for p in coords:
            polygon.append(QtCore.QPointF(*p))
        self.qpainter.drawPolygon(polygon)

        self.qpainter.restore()

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        self.qpainter.save()

        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2-x1)
        h = abs(y2-y1)

        if fill is not None:
            self.qpainter.fillRect(x, y, w, h, QColor(fill))

        if stroke is not None:
            pen = self.qpainter.pen()

            pen.setColor(QColor(stroke))
            pen.setWidth(width)
            self.qpainter.setPen(pen)
            self.qpainter.drawRect(x, y, w, h)

        self.qpainter.restore()

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()

        if fill is not None:
            self.qpainter.setBrush(QColor(fill))

        if stroke is not None:
            pen.setColor(QColor(stroke))
            pen.setWidth(width)

        self.qpainter.setPen(pen)
        self.qpainter.drawEllipse(QtCore.QPointF(x,y), rx, ry)

        self.qpainter.restore()
