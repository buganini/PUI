from .. import *
from .base import *

from PySide6 import QtWidgets, QtGui
from PySide6.QtGui import QPainter, QColor, QPainterPath, QImage

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
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._dblclicked(e)

    def mousePressEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mousedown(e)

    def mouseReleaseEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mouseup(e)

    def mouseMoveEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.node._mousemove(e)

    def wheelEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        e.y_delta = event.pixelDelta().y()
        e.x_delta = event.pixelDelta().x()
        e.v_delta = event.angleDelta().y()
        e.h_delta = event.angleDelta().x()
        modifier = 0
        emodifiers = event.modifiers()
        if emodifiers & QtCore.Qt.ShiftModifier:
            modifier |= KeyModifier.SHIFT
        if emodifiers & QtCore.Qt.ControlModifier:
            modifier |= KeyModifier.CTRL
        if emodifiers & QtCore.Qt.AltModifier:
            modifier |= KeyModifier.ALT
        if emodifiers & QtCore.Qt.MetaModifier:
            modifier |= KeyModifier.META
        e.modifiers = modifier
        self.node._wheel(e)

    def paintEvent(self, event):
        node = self.node.get_node()
        node.qpainter = QPainter()
        node.qpainter.begin(self)
        node.qpainter.setRenderHints(QtGui.QPainter.Antialiasing, True)

        if not node.style_bgcolor is None:
            bgBrush = QtGui.QBrush()
            bgBrush.setColor(QtGui.QColor(node.style_bgcolor))
            bgBrush.setStyle(QtCore.Qt.SolidPattern)
            rect = QtCore.QRect(0, 0, self.width or self.geometry().width(), self.height or self.geometry().height())
            node.qpainter.fillRect(rect, bgBrush)

        node.width = self.geometry().width()
        node.height = self.geometry().height()
        immediate = node.painter(node, *node.args)
        node.qpainter.end()
        node.qpainter = None
        if immediate:
            self.update()

class ImageResource():
    def crop(self, x, y, width, height):
        ir = ImageResource()
        ir.qimage = self.qimage.copy(x, y, width, height)
        return ir

    def scale(self, width, height, keepAspectRatio=True, quality=0):
        ir = ImageResource()
        method = {
            0: QtCore.Qt.TransformationMode.FastTransformation
        }.get(quality, QtCore.Qt.TransformationMode.SmoothTransformation)
        ir.qimage = self.qimage.scaled(width, height, QtCore.Qt.AspectRatioMode.KeepAspectRatio if keepAspectRatio else QtCore.Qt.IgnoreAspectRatio, method)
        return ir

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

    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
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

        if size is not None:
            font = self.qpainter.font()
            font.setPointSize(size)
            self.qpainter.setFont(font)

        if color is not None:
            self.qpainter.setPen(QColor(color))

        self.qpainter.drawText(0, 0, w, h, 0, text)
        self.qpainter.restore()

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()
        if color is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(color))
            pen.setWidth(width)
        self.qpainter.setPen(pen)

        self.qpainter.drawLine(x1, y1, x2, y2)

        self.qpainter.restore()

    def drawPolyline(self, coords, color=None, width=1):
        self.qpainter.save()

        pen = self.qpainter.pen()
        if color is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(color))
            pen.setWidth(width)
        self.qpainter.setPen(pen)

        self.qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in coords])

        self.qpainter.restore()

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        self.qpainter.save()

        brush = self.qpainter.brush()
        if fill is None:
            brush.setStyle(QtCore.Qt.NoBrush)
        else:
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QColor(fill))
        self.qpainter.setBrush(brush)

        pen = self.qpainter.pen()
        if stroke is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
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

        brush = self.qpainter.brush()
        if fill is None:
            brush.setStyle(QtCore.Qt.NoBrush)
        else:
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QColor(fill))
        self.qpainter.setBrush(brush)

        pen = self.qpainter.pen()
        if stroke is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(stroke))
            pen.setWidth(width)
        self.qpainter.setPen(pen)

        self.qpainter.drawRect(x, y, w, h)

        self.qpainter.restore()

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        self.qpainter.save()

        brush = self.qpainter.brush()
        if fill is None:
            brush.setStyle(QtCore.Qt.NoBrush)
        else:
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QColor(fill))
        self.qpainter.setBrush(brush)

        pen = self.qpainter.pen()
        if stroke is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(stroke))
            pen.setWidth(width)
        self.qpainter.setPen(pen)

        self.qpainter.drawEllipse(QtCore.QPointF(x,y), rx, ry)

        self.qpainter.restore()

    def drawShapely(self, shape, fill=None, stroke=None, width=1):
        self.qpainter.save()

        brush = self.qpainter.brush()
        if fill is None:
            brush.setStyle(QtCore.Qt.NoBrush)
        else:
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QColor(fill))
        self.qpainter.setBrush(brush)

        pen = self.qpainter.pen()
        if stroke is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(stroke))
            pen.setWidth(width)
        self.qpainter.setPen(pen)

        self._drawShapely(shape, fill, stroke, width)

        self.qpainter.restore()


    def _drawShapely(self, shape, fill=None, stroke=None, width=1):
        if hasattr(shape, "geoms"):
            for g in shape.geoms:
                self.drawShapely(g, fill, stroke, width)
        elif hasattr(shape, "exterior"): # polygon
            path = QPainterPath()

            exterior = QtGui.QPolygonF()
            for p in shape.exterior.coords:
                exterior.append(QtCore.QPointF(*p))
            path.addPolygon(exterior)

            for h in shape.interiors:
                hole = QtGui.QPolygonF()
                for p in h.coords:
                    hole.append(QtCore.QPointF(*p))
                hpoly = QPainterPath()
                hpoly.addPolygon(hole)
                path = path.subtracted(hpoly)

            self.qpainter.drawPath(path)
        elif hasattr(shape, "x") and hasattr(shape, "y"): # point
            self.drawEllipse(shape.x, shape.y, width/2, width/2, fill=stroke)
        elif hasattr(shape, "coords"): # linestring, linearring
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise RuntimeError(f"Not implemented: drawShapely({type(shape).__name__}) {dir(shape)}")

    def loadImage(self, image_path):
        ir = ImageResource()
        ir.qimage = QImage(image_path)
        return ir

    def drawImage(self, image, x=0, y=0, width=None, height=None, src_x=0, src_y=0, src_width=None, src_height=None, opacity=1.0):
        if image.qimage.isNull():
            return

        if src_width is None:
            src_width = image.qimage.width() - src_x
        if src_height is None:
            src_height = image.qimage.height() - src_y

        source_rect = QtCore.QRect(src_x, src_y, src_width, src_height)

        if width is None:
            width = src_width
        if height is None:
            height = src_height

        dest_rect = QtCore.QRect(x, y, width, height)
        self.qpainter.setOpacity(opacity)
        self.qpainter.drawImage(dest_rect, image.qimage, source_rect)
        self.qpainter.setOpacity(1.0)