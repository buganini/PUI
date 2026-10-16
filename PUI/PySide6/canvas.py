from .. import *
from .base import *

from PySide6 import QtWidgets, QtGui
from PySide6.QtGui import QPainter, QColor, QPainterPath, QImage, QPen, QBrush

class PUIQtCanvas(QtWidgets.QWidget):
    def __init__(self, node, width=None, height=None):
        self.puinode = node
        self.width = width
        self.height = height
        super().__init__()

    def minimumSizeHint(self):
        return QtCore.QSize(self.width, self.height)

    def mouseDoubleClickEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.puinode._dblclicked(e)

    def mousePressEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.puinode._mousedown(e)

    def mouseReleaseEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.puinode._mouseup(e)

    def mouseMoveEvent(self, event):
        e = PUIEvent()
        e.button = event.button().value
        e.x, e.y = event.position().toPoint().toTuple()
        self.puinode._mousemove(e)

    def enterEvent(self, event):
        e = PUIEvent()
        e.x, e.y = event.position().toPoint().toTuple()
        self.puinode._mouseenter(e)
        super().enterEvent(event)

    def leaveEvent(self, event):
        e = PUIEvent()
        cursor = self.mapFromGlobal(QtGui.QCursor.pos())
        e.x, e.y = cursor.x(), cursor.y()
        self.puinode._mouseleave(e)
        super().leaveEvent(event)

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
        self.puinode._wheel(e)

    def paintEvent(self, event):
        puinode = self.puinode.get_node()
        puinode.pixel_density = max(1.0, float(self.devicePixelRatioF()))
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        puinode._begin_paint(painter)
        try:
            if puinode.style_bgcolor is not None:
                rect = QtCore.QRect(0, 0, self.width or self.geometry().width(), self.height or self.geometry().height())
                painter.fillRect(rect, QColor(puinode.style_bgcolor))

            puinode.width = self.geometry().width()
            puinode.height = self.geometry().height()
            immediate = puinode.painter(puinode, *puinode.args)
        finally:
            painter.end()
            puinode._end_paint()
        if immediate:
            self.update()

class ImageResource():
    @staticmethod
    def load(path):
        ir = ImageResource()
        ir.qimage = QImage(path)
        return ir

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
        self.pixel_density = 1.0
        self._qpainter = None

    @property
    def qpainter(self):
        # A caller may retain this reference and change styles between helpers.
        # Keep setters unconditional for the remainder of this paint.
        self._cache_styles = False
        return self._qpainter

    @qpainter.setter
    def qpainter(self, painter):
        self._cache_styles = False
        self._qpainter = painter

    def _begin_paint(self, painter):
        self._qpainter = painter
        # Helpers set their own pen/brush. Defaults and cached Qt objects belong
        # to this paint only, so styles cannot leak between frames or widgets.
        self._default_pen = painter.pen()
        self._default_brush = painter.brush()
        self._cache_styles = True
        self._last_pen = self._last_brush = None
        self._pens = {}
        self._brushes = {}

    def _end_paint(self):
        self._qpainter = None
        self._cache_styles = False
        self._last_pen = self._last_brush = None
        self._default_pen = self._default_brush = None
        self._pens.clear()
        self._brushes.clear()

    def _pen(self, color, width):
        key = (color, width)
        try:
            return self._pens[key]
        except (KeyError, TypeError):
            pass
        pen = QPen(self._default_pen)
        if color is None:
            pen.setStyle(QtCore.Qt.NoPen)
        else:
            pen.setStyle(QtCore.Qt.SolidLine)
            pen.setColor(QColor(color))
            pen.setWidth(width)
        try:
            self._pens[key] = pen
        except TypeError:
            # QColor and other unhashable Qt color inputs still work, without
            # retaining mutable objects as cache keys.
            pass
        return pen

    def _brush(self, color):
        try:
            return self._brushes[color]
        except (KeyError, TypeError):
            pass
        brush = QBrush(self._default_brush)
        if color is None:
            brush.setStyle(QtCore.Qt.NoBrush)
        else:
            brush.setStyle(QtCore.Qt.SolidPattern)
            brush.setColor(QColor(color))
        try:
            self._brushes[color] = brush
        except TypeError:
            pass
        return brush

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
        self._qpainter.save()
        try:
            # NoPen from a preceding fill-only shape also suppresses Qt's
            # boundingRect measurement, so restore the text default first.
            self._qpainter.setPen(self._default_pen)
            br = self._qpainter.boundingRect(0, 0, w, h, 0, text)

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

            self._qpainter.translate(int(x+dx), int(y+dy))
            self._qpainter.rotate(rotate)
            self._qpainter.translate(int(-dx), int(-dy))

            if size is not None:
                font = self._qpainter.font()
                font.setPointSize(size)
                self._qpainter.setFont(font)

            if color is not None:
                self._qpainter.setPen(QColor(color))
            self._qpainter.drawText(0, 0, w, h, 0, text)
        finally:
            self._qpainter.restore()

    def drawLine(self, x1, y1, x2, y2, color=None, width=1):
        pen = self._pen(color, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen
        self._qpainter.drawLine(x1, y1, x2, y2)

    def drawPolyline(self, coords, color=None, width=1):
        pen = self._pen(color, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen
        self._qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in coords])

    def drawCubicBezier(self, start, control1, control2, end, color=None, width=1):
        brush = self._brush(None)
        if not self._cache_styles or brush is not self._last_brush:
            self._qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(color, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen

        path = QPainterPath(QtCore.QPointF(*start))
        path.cubicTo(
            QtCore.QPointF(*control1),
            QtCore.QPointF(*control2),
            QtCore.QPointF(*end),
        )
        self._qpainter.drawPath(path)

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        brush = self._brush(fill)
        if not self._cache_styles or brush is not self._last_brush:
            self._qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen

        polygon = QtGui.QPolygonF()
        for p in coords:
            polygon.append(QtCore.QPointF(*p))
        self._qpainter.drawPolygon(polygon)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2-x1)
        h = abs(y2-y1)

        brush = self._brush(fill)
        if not self._cache_styles or brush is not self._last_brush:
            self._qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen
        self._qpainter.drawRect(x, y, w, h)

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        brush = self._brush(fill)
        if not self._cache_styles or brush is not self._last_brush:
            self._qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if not self._cache_styles or pen is not self._last_pen:
            self._qpainter.setPen(pen)
            self._last_pen = pen
        self._qpainter.drawEllipse(QtCore.QPointF(x,y), rx, ry)

    def drawShapely(self, shape, fill=None, stroke=None, width=1):
        self._drawShapely(shape, fill, stroke, width)

    def _drawShapely(self, shape, fill=None, stroke=None, width=1):
        if hasattr(shape, "geoms"):
            for g in shape.geoms:
                self.drawShapely(g, fill, stroke, width)
        elif hasattr(shape, "exterior"): # polygon
            brush = self._brush(fill)
            if not self._cache_styles or brush is not self._last_brush:
                self._qpainter.setBrush(brush)
                self._last_brush = brush
            pen = self._pen(stroke, width)
            if not self._cache_styles or pen is not self._last_pen:
                self._qpainter.setPen(pen)
                self._last_pen = pen
            path = QPainterPath()
            path.setFillRule(QtCore.Qt.FillRule.OddEvenFill)

            exterior = QtGui.QPolygonF()
            for p in shape.exterior.coords:
                exterior.append(QtCore.QPointF(*p))
            path.addPolygon(exterior)
            path.closeSubpath()

            for i,h in enumerate(shape.interiors):
                hole = QtGui.QPolygonF()
                for p in h.coords:
                    hole.append(QtCore.QPointF(*p))
                path.addPolygon(hole)
                path.closeSubpath()

            self._qpainter.drawPath(path)
        elif hasattr(shape, "x") and hasattr(shape, "y"): # point
            self.drawEllipse(shape.x, shape.y, width/2, width/2, fill=stroke)
        elif hasattr(shape, "coords"): # linestring, linearring
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise RuntimeError(f"Not implemented: drawShapely({type(shape).__name__}) {dir(shape)}")

    def loadImage(self, image_path):
        return ImageResource.load(image_path)

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
        self._qpainter.save()
        try:
            self._qpainter.setOpacity(opacity)
            self._qpainter.drawImage(dest_rect, image.qimage, source_rect)
        finally:
            self._qpainter.restore()
