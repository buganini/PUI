from __future__ import annotations
from .. import _typing as _t
from .._canvas import CanvasScope
from .._path import path_commands, fill_rule, FillRule
from .._rgba import RGBAImage
from .. import *
from .._canvas import FrameRate
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
                painter.fillRect(rect, qcolor(puinode.style_bgcolor))

            puinode.width = self.geometry().width()
            puinode.height = self.geometry().height()
            immediate = puinode.painter(puinode, *puinode.args)
        finally:
            painter.end()
            puinode._end_paint()
        if puinode.show_fps:
            if not hasattr(self, '_fps'):
                self._fps = FrameRate()
                self._fps_label = QtWidgets.QLabel(self)
                self._fps_label.setStyleSheet('background: #101a2b; color: white; padding: 4px;')
                self._fps_label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
            text = self._fps.tick()
            if text is not None:
                self._fps_label.setText(text)
                self._fps_label.adjustSize()
            self._fps_label.move(max(0, self.geometry().width() - self._fps_label.width() - 8), 8)
            self._fps_label.show()
        elif hasattr(self, '_fps'):
            self._fps_label.deleteLater()
            del self._fps, self._fps_label
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

class Canvas(CanvasScope, QtBaseWidget):
    expand_x_prio = expand_y_prio = 4
    def __init__(self, painter: _t.Callback, *args: _t.Any, show_fps: bool = False) -> None:
        super().__init__()
        self.ui = None
        self.show_fps = show_fps
        self.painter = painter
        self.args = args
        self.pixel_density = 1.0
        self.qpainter = None

    def _begin_paint(self, painter):
        self.qpainter = painter
        # Helpers set their own pen/brush. Defaults and cached Qt objects belong
        # to this paint only, so styles cannot leak between frames or widgets.
        self._default_pen = painter.pen()
        self._default_brush = painter.brush()
        self._last_pen = self._last_brush = None
        self._paint_stack = []
        self._pens = {}
        self._brushes = {}

    def _end_paint(self):
        self.qpainter = None
        self._default_pen = self._default_brush = None
        self._last_pen = self._last_brush = None
        self._paint_stack.clear()
        self._pens.clear()
        self._brushes.clear()

    def push(self) -> None:
        """Save native painter state and PUI style tracking for this paint."""
        if self.qpainter is None:
            raise RuntimeError('Canvas.push() requires an active painter')
        self.qpainter.save()
        self._paint_stack.append((self._last_pen, self._last_brush))

    def pop(self) -> None:
        """Restore the matching push, including PUI style tracking."""
        if self.qpainter is None:
            raise RuntimeError('Canvas.pop() requires an active painter')
        if not self._paint_stack:
            raise RuntimeError('Canvas.pop() has no matching push()')
        self.qpainter.restore()
        self._last_pen, self._last_brush = self._paint_stack.pop()

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
            pen.setColor(qcolor(color))
            pen.setWidthF(width)
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
            brush.setColor(qcolor(color))
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

    def drawText(
        self,
        x: _t.Number,
        y: _t.Number,
        text: _t.Any,
        w: _t.Number | None = None,
        h: _t.Number | None = None,
        size: _t.Number = 12,
        color: int | None = None,
        rotate: _t.Number = 0,
        anchor: Anchor = Anchor.LeftTop,
    ) -> None:
        if w is None:
            w = self.ui.geometry().width()
        if h is None:
            h = self.ui.geometry().height()
        self.qpainter.save()
        try:
            # NoPen from a preceding fill-only shape also suppresses Qt's
            # boundingRect measurement, so restore the text default first.
            self.qpainter.setPen(self._default_pen)
            br = self.qpainter.boundingRect(0, 0, w, h, 0, text)

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

            self.qpainter.translate(int(x+dx), int(y+dy))
            self.qpainter.rotate(rotate)
            self.qpainter.translate(int(-dx), int(-dy))

            if size is not None:
                font = self.qpainter.font()
                font.setPointSize(size)
                self.qpainter.setFont(font)

            if color is not None:
                self.qpainter.setPen(qcolor(color))
            self.qpainter.drawText(0, 0, w, h, 0, text)
        finally:
            self.qpainter.restore()

    def drawLine(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        pen = self._pen(color, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen
        self.qpainter.drawLine(x1, y1, x2, y2)

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        pen = self._pen(color, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen
        self.qpainter.drawPolyline([QtCore.QPointF(x,y) for x,y in coords])

    def drawCubicBezier(
        self,
        start: _t.Point,
        control1: _t.Point,
        control2: _t.Point,
        end: _t.Point,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        brush = self._brush(None)
        if brush is not self._last_brush:
            self.qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(color, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen

        path = QPainterPath(QtCore.QPointF(*start))
        path.cubicTo(
            QtCore.QPointF(*control1),
            QtCore.QPointF(*control2),
            QtCore.QPointF(*end),
        )
        self.qpainter.drawPath(path)

    def drawPolygon(
        self,
        coords: _t.Points,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen

        polygon = QtGui.QPolygonF()
        for p in coords:
            polygon.append(QtCore.QPointF(*p))
        self.qpainter.drawPolygon(polygon)

    def drawRect(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2-x1)
        h = abs(y2-y1)

        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen
        self.qpainter.drawRect(x, y, w, h)

    def drawEllipse(
        self,
        x: _t.Number,
        y: _t.Number,
        rx: _t.Number,
        ry: _t.Number,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.qpainter.setBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.qpainter.setPen(pen)
            self._last_pen = pen
        self.qpainter.drawEllipse(QtCore.QPointF(x,y), rx, ry)

    def drawShapely(
        self,
        shape: _t.Any,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        self._drawShapely(shape, fill, stroke, width)

    def _drawShapely(self, shape, fill=None, stroke=None, width=1):
        if hasattr(shape, "geoms"):
            for g in shape.geoms:
                self.drawShapely(g, fill, stroke, width)
        elif hasattr(shape, "exterior"): # polygon
            brush = self._brush(fill)
            if brush is not self._last_brush:
                self.qpainter.setBrush(brush)
                self._last_brush = brush
            pen = self._pen(stroke, width)
            if pen is not self._last_pen:
                self.qpainter.setPen(pen)
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

            self.qpainter.drawPath(path)
        elif hasattr(shape, "x") and hasattr(shape, "y"): # point
            self.drawEllipse(shape.x, shape.y, width/2, width/2, fill=stroke)
        elif hasattr(shape, "coords"): # linestring, linearring
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise RuntimeError(f"Not implemented: drawShapely({type(shape).__name__}) {dir(shape)}")

    def loadImage(self, image_path: _t.Any) -> ImageResource:
        return ImageResource.load(image_path)

    def drawImage(
        self,
        image: ImageResource,
        x: _t.Number = 0,
        y: _t.Number = 0,
        width: _t.Number | None = None,
        height: _t.Number | None = None,
        src_x: _t.Number = 0,
        src_y: _t.Number = 0,
        src_width: _t.Number | None = None,
        src_height: _t.Number | None = None,
        opacity: _t.Number = 1.0,
    ) -> None:
        if isinstance(image, RGBAImage):
            resource = ImageResource()
            resource.qimage = QImage(image.data, image.width, image.height, image.width * 4,
                                     QImage.Format_RGBA8888).copy()
            image = resource
        if image.qimage.isNull():
            return

        if src_width is None:
            src_width = image.qimage.width() - src_x
        if src_height is None:
            src_height = image.qimage.height() - src_y

        source_rect = QtCore.QRectF(src_x, src_y, src_width, src_height)

        if width is None:
            width = src_width
        if height is None:
            height = src_height

        dest_rect = QtCore.QRectF(x, y, width, height)
        self.qpainter.save()
        try:
            self.qpainter.setOpacity(opacity)
            self.qpainter.drawImage(dest_rect, image.qimage, source_rect)
        finally:
            self.qpainter.restore()

    supports_path_clip = True

    def _native_path(self, commands, rule):
        path = QPainterPath()
        for op, *values in commands:
            if op == 'Z': path.closeSubpath()
            else: getattr(path, {'M':'moveTo', 'L':'lineTo', 'Q':'quadTo', 'C':'cubicTo'}[op])(*values)
        path.setFillRule(QtCore.Qt.WindingFill if rule == 'nonzero' else QtCore.Qt.OddEvenFill)
        return path

    def drawPath(self, path, fill=None, stroke=None, width=1, fillRule=FillRule.NonZero):
        native = self._native_path(path_commands(path), fill_rule(fillRule))
        self.qpainter.save()
        try:
            self.qpainter.setPen(self._pen(stroke, width))
            self.qpainter.setBrush(self._brush(fill))
            self.qpainter.drawPath(native)
        finally:
            self.qpainter.restore()

    def clipRect(self, x, y, width, height):
        self.qpainter.setClipRect(QtCore.QRectF(x, y, width, height), QtCore.Qt.IntersectClip)

    def clipPath(self, path, fillRule=FillRule.NonZero):
        self.qpainter.setClipPath(self._native_path(path_commands(path), fill_rule(fillRule)), QtCore.Qt.IntersectClip)
