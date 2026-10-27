from __future__ import annotations
from .. import _typing as _t
from .._canvas import CanvasScope
from .._path import path_commands, fill_rule, FillRule
from .._rgba import RGBAImage
from .. import *
from .._canvas import FrameRate
from .base import *
import math

class ImageResource:
    @staticmethod
    def load(path):
        resource = ImageResource()
        resource.image = wx.Image(str(path))
        return resource

    def crop(self, x, y, width, height):
        resource = ImageResource()
        resource.image = self.image.GetSubImage(wx.Rect(int(x), int(y), int(width), int(height)))
        return resource

    def scale(self, width, height, keepAspectRatio=True, quality=0):
        resource = ImageResource()
        if keepAspectRatio:
            ratio = min(width / self.image.GetWidth(), height / self.image.GetHeight())
            width, height = self.image.GetWidth() * ratio, self.image.GetHeight() * ratio
        resource.image = self.image.Scale(max(1, int(width)), max(1, int(height)),
                                         wx.IMAGE_QUALITY_NORMAL if quality == 0 else wx.IMAGE_QUALITY_HIGH)
        return resource


class Canvas(CanvasScope, WxBaseWidget):
    expand_x_prio = 4
    expand_y_prio = 4

    def __init__(self, painter: _t.Callback, *args: _t.Any, show_fps: bool = False) -> None:
        super().__init__()
        self.ui = None
        self.show_fps = show_fps
        self.painter = painter
        self.args = args
        self.pixel_density = 1.0
        self.dc = None
        self._last_pen = self._last_brush = None
        self._paint_stack = []
        self._clips = []
        self._pens = {}
        self._brushes = {}
        self._fonts = {}

    def push(self) -> None:
        """Save DC pen/brush, PUI tracking and PUI clipping regions."""
        if self.dc is None:
            raise RuntimeError('Canvas.push() requires an active painter')
        self._paint_stack.append((wx.Pen(self.dc.GetPen()), wx.Brush(self.dc.GetBrush()),
                                  self._last_pen, self._last_brush, list(self._clips)))

    def pop(self) -> None:
        """Restore pen/brush and tracking from the matching push."""
        if self.dc is None:
            raise RuntimeError('Canvas.pop() requires an active painter')
        if not self._paint_stack:
            raise RuntimeError('Canvas.pop() has no matching push()')
        pen, brush, last_pen, last_brush, self._clips = self._paint_stack.pop()
        self._restore_clip()
        self.dc.SetPen(pen)
        self.dc.SetBrush(brush)
        self._last_pen, self._last_brush = last_pen, last_brush

    def _pen(self, color, width):
        if color is None:
            return wx.NullPen
        key = (color, width)
        if key not in self._pens:
            self._pens[key] = wx.Pen(int_to_wx_colour(color), width)
        return self._pens[key]

    def _brush(self, color):
        if color is None:
            return wx.TRANSPARENT_BRUSH
        if color not in self._brushes:
            self._brushes[color] = wx.Brush(int_to_wx_colour(color))
        return self._brushes[color]

    def _font(self, size):
        if size not in self._fonts:
            font = wx.Font(self.ui.GetFont())
            if size is not None:
                font.SetFractionalPointSize(float(size))
            self._fonts[size] = font
        return self._fonts[size]

    def _clear_paint_styles(self):
        self._last_pen = self._last_brush = None
        self._paint_stack.clear()
        self._clips.clear()
        self._pens.clear()
        self._brushes.clear()
        self._fonts.clear()


    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.width = self.layout_width or 0
            self.height = self.layout_height or 0
            self.ui.Unbind(wx.EVT_PAINT)
            self.ui.Unbind(wx.EVT_LEFT_DCLICK)
            self.ui.Unbind(wx.EVT_LEFT_DOWN)
            self.ui.Unbind(wx.EVT_LEFT_UP)
            self.ui.Unbind(wx.EVT_MOTION)
            self.ui.Unbind(wx.EVT_MOUSEWHEEL)
            self.ui.Unbind(wx.EVT_ENTER_WINDOW)
            self.ui.Unbind(wx.EVT_LEAVE_WINDOW)
            self.ui.Refresh()
        else:
            self.ui = wx.Panel(getWindow(self.parent))
            self.width = self.layout_width or 0
            self.height = self.layout_height or 0
            self.ui.SetMinSize((self.width, self.height))
        self.ui.Bind(wx.EVT_PAINT, self._paint)
        self.ui.Bind(wx.EVT_LEFT_DCLICK, self._LeftDblClick)
        self.ui.Bind(wx.EVT_LEFT_DOWN, self._LeftDown)
        self.ui.Bind(wx.EVT_LEFT_UP, self._LeftUp)
        self.ui.Bind(wx.EVT_MOTION, self._Motion)
        self.ui.Bind(wx.EVT_MOUSEWHEEL, self._MouseWheel)
        self.ui.Bind(wx.EVT_ENTER_WINDOW, self._Enter)
        self.ui.Bind(wx.EVT_LEAVE_WINDOW, self._Leave)

        super().update(prev)

    def _MouseWheel(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
            e.h_delta = 0
            e.v_delta = event.GetWheelRotation()
            e.x_delta = 0
            e.y_delta = 0
        else:
            e.h_delta = event.GetWheelRotation()
            e.v_delta = 0
            e.x_delta = 0
            e.y_delta = 0
        e.modifiers = 0
        for check, flag in ((event.ShiftDown, KeyModifier.SHIFT),
                            (event.ControlDown, KeyModifier.CTRL),
                            (event.AltDown, KeyModifier.ALT),
                            (event.MetaDown, KeyModifier.META)):
            if check():
                e.modifiers |= flag
        self.get_node()._wheel(e)

    def _LeftDblClick(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        e.button = MouseButton.LEFT if event.LeftIsDown() or event.GetButton() == wx.MOUSE_BTN_LEFT else MouseButton.NONE
        self.get_node()._dblclicked(e)

    def _LeftDown(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        e.button = MouseButton.LEFT if event.LeftIsDown() or event.GetButton() == wx.MOUSE_BTN_LEFT else MouseButton.NONE
        self.get_node()._mousedown(e)

    def _LeftUp(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        e.button = MouseButton.LEFT if event.LeftIsDown() or event.GetButton() == wx.MOUSE_BTN_LEFT else MouseButton.NONE
        self.get_node()._mouseup(e)

    def _Motion(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        e.button = MouseButton.LEFT if event.LeftIsDown() or event.GetButton() == wx.MOUSE_BTN_LEFT else MouseButton.NONE
        self.get_node()._mousemove(e)

    def _Enter(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._mouseenter(e)
        event.Skip()

    def _Leave(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._mouseleave(e)
        event.Skip()

    def _paint(self, event):
        node = self.get_node()
        if node.destroyed or not node.ui or node.ui.IsBeingDeleted():
            return

        try:
            node.pixel_density = max(
                1.0, float(node.ui.GetContentScaleFactor())
            )
        except (AttributeError, TypeError, ValueError):
            node.pixel_density = 1.0

        node.dc = wx.PaintDC(node.ui)
        if not node.style_bgcolor is None:
            original_brush = node.dc.GetBrush()
            node.dc.SetBrush(wx.Brush(int_to_wx_colour(node.style_bgcolor)))
            node.dc.DrawRectangle(node.ui.GetClientRect())
            node.dc.SetBrush(original_brush)

        node.width, node.height = node.ui.GetClientSize()
        node._clear_paint_styles()
        try:
            immediate = node.painter(node, *node.args)
        finally:
            node.dc = None
            node._clear_paint_styles()
        if node.show_fps:
            if not hasattr(node.ui, '_fps'):
                node.ui._fps = FrameRate()
                node.ui._fps_label = wx.StaticText(node.ui, label='FPS: ...')
                node.ui._fps_label.SetBackgroundColour(wx.Colour('#101a2b'))
                node.ui._fps_label.SetForegroundColour(wx.WHITE)
            text = node.ui._fps.tick()
            if text is not None:
                node.ui._fps_label.SetLabel(text)
            node.ui._fps_label.SetPosition((max(0, node.width - node.ui._fps_label.GetBestSize().width - 8), 8))
        elif hasattr(node.ui, '_fps'):
            node.ui._fps_label.Destroy()
            del node.ui._fps, node.ui._fps_label
        if immediate:
            node.ui.Refresh(False)


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
        text = str(text)
        if not text or (size is not None and size <= 0) or any(v is not None and v <= 0 for v in (w, h)):
            return
        gc = self._graphics_context()
        gc.PushState()
        try:
            foreground = self.ui.GetForegroundColour() if color is None else int_to_wx_colour(color)
            # Measure on the same GraphicsContext/font that draws the text;
            # the DC's font can differ from the requested point size.
            gc.SetFont(self._font(size), foreground)
            lines = text.split('\n')
            width = max(gc.GetTextExtent(line)[0] for line in lines)
            line_height = gc.GetTextExtent('Mg')[1]
            height = line_height * len(lines)
            ax = {'left': 0, 'center': .5, 'right': 1}[anchor.value[0]]
            ay = {'top': 0, 'center': .5, 'bottom': 1}[anchor.value[1]]
            gc.Translate(x, y)
            gc.Rotate(math.radians(rotate))
            gc.Translate(-ax * width, -ay * height)
            if w is not None or h is not None:
                gc.Clip(0, 0, width if w is None else w, height if h is None else h)
            for index, line in enumerate(lines):
                gc.DrawText(line, 0, index * line_height)
        finally:
            gc.PopState()

    def drawLine(
        self,
        x1: _t.Number,
        y1: _t.Number,
        x2: _t.Number,
        y2: _t.Number,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if color is not None and color > 0xFFFFFF:
            return self.drawPath([(self.PathOp.MoveTo,x1,y1),(self.PathOp.LineTo,x2,y2)],stroke=color,width=width)
        if color is None:
            return
        pen = self._pen(color, width)
        if pen is not self._last_pen:
            self.dc.SetPen(pen)
            self._last_pen = pen
        self.dc.DrawLine(int(x1), int(y1), int(x2), int(y2))

    def drawPolyline(self, coords: _t.Points, color: int | None = None, width: _t.Number = 1) -> None:
        if color is not None and color > 0xFFFFFF:
            coords=list(coords)
            return self.drawPath([(self.PathOp.MoveTo if i==0 else self.PathOp.LineTo,*p) for i,p in enumerate(coords)],stroke=color,width=width)
        if color is None:
            return
        pen = self._pen(color, width)
        if pen is not self._last_pen:
            self.dc.SetPen(pen)
            self._last_pen = pen
        coords = [(int(c[0]), int(c[1])) for c in coords]
        self.dc.DrawLines(coords)

    def drawPolygon(
        self,
        coords: _t.Points,
        fill: int | None = None,
        stroke: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if any(c is not None and c > 0xFFFFFF for c in (fill,stroke)):
            coords=list(coords)
            if not coords: return
            path=[(self.PathOp.MoveTo if i==0 else self.PathOp.LineTo,*p) for i,p in enumerate(coords)]+[(self.PathOp.Close,)]
            return self.drawPath(path,fill,stroke,width,self.FillRule.EvenOdd)
        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.dc.SetBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.dc.SetPen(pen)
            self._last_pen = pen

        coords = [(int(c[0]), int(c[1])) for c in coords]
        self.dc.DrawPolygon(coords)

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
        if any(c is not None and c > 0xFFFFFF for c in (fill,stroke)):
            O=self.PathOp
            return self.drawPath([(O.MoveTo,x1,y1),(O.LineTo,x2,y1),(O.LineTo,x2,y2),(O.LineTo,x1,y2),(O.Close,)],fill,stroke,width)
        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.dc.SetBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.dc.SetPen(pen)
            self._last_pen = pen

        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        self.dc.DrawRectangle(int(x), int(y), int(w), int(h))

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
        if any(c is not None and c > 0xFFFFFF for c in (fill,stroke)):
            gc=self._graphics_context()
            native=gc.CreatePath();native.AddEllipse(x-rx,y-ry,rx*2,ry*2)
            if fill is not None:
                gc.SetBrush(self._brush(fill));gc.FillPath(native)
            if stroke is not None:
                gc.SetPen(gc.CreatePen(wx.GraphicsPenInfo(int_to_wx_colour(stroke)).Width(width)));gc.StrokePath(native)
            return
        brush = self._brush(fill)
        if brush is not self._last_brush:
            self.dc.SetBrush(brush)
            self._last_brush = brush
        pen = self._pen(stroke, width)
        if pen is not self._last_pen:
            self.dc.SetPen(pen)
            self._last_pen = pen

        self.dc.DrawEllipse(int(x-rx), int(y-ry), int(rx*2), int(ry*2))

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
            gc = self._graphics_context()
            if gc:
                path = gc.CreatePath()

                exterior = shape.exterior.coords
                path.MoveToPoint(* exterior[0])
                for point in exterior[1:]:
                    path.AddLineToPoint(*point)
                path.CloseSubpath()

                for hole in shape.interiors:
                    hole = hole.coords
                    path.MoveToPoint(*hole[0])
                    # Draw holes in reverse order
                    for point in hole[1:]:
                        path.AddLineToPoint(*point)
                    path.CloseSubpath()

                gc.SetBrush(self._brush(fill))
                gc.SetPen(wx.TRANSPARENT_PEN if stroke is None else self._pen(stroke, width))
                gc.DrawPath(path, wx.ODDEVEN_RULE)
        elif hasattr(shape, "x") and hasattr(shape, "y"): # point
            self.drawEllipse(shape.x, shape.y, width/2, width/2, fill=stroke)
        elif hasattr(shape, "coords"): # linestring, linearring
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise RuntimeError(f"Not implemented: drawShapely({type(shape).__name__}) {dir(shape)}")

    def drawCubicBezier(
        self,
        start: _t.Point,
        control1: _t.Point,
        control2: _t.Point,
        end: _t.Point,
        color: int | None = None,
        width: _t.Number = 1,
    ) -> None:
        if color is None:
            return
        gc = self._graphics_context()
        gc.SetPen(self._pen(color, width))
        path = gc.CreatePath()
        path.MoveToPoint(*start)
        path.AddCurveToPoint(*control1, *control2, *end)
        gc.StrokePath(path)

    def loadImage(self, image_path: _t.Any) -> ImageResource:
        return ImageResource.load(image_path)

    def drawImage(self, image: ImageResource, x: _t.Number = 0, y: _t.Number = 0, width: _t.Number | None = None, height: _t.Number | None = None,
                  src_x: _t.Number = 0, src_y: _t.Number = 0, src_width: _t.Number | None = None, src_height: _t.Number | None = None, opacity: _t.Number = 1.0) -> None:
        if isinstance(image, RGBAImage):
            resource = ImageResource()
            resource.image = wx.Image(image.width, image.height)
            resource.image.SetData(bytes(v for i,v in enumerate(image.data) if i % 4 != 3))
            resource.image.SetAlpha(image.data[3::4])
            image = resource
        if not image.image.IsOk():
            return
        source = image.image
        src_width = source.GetWidth() - src_x if src_width is None else src_width
        src_height = source.GetHeight() - src_y if src_height is None else src_height
        source = source.GetSubImage(wx.Rect(int(src_x), int(src_y), int(src_width), int(src_height)))
        if opacity < 1:
            if not source.HasAlpha():
                source.InitAlpha()
            source.SetAlpha(bytes(int(value * max(0, opacity)) for value in source.GetAlpha()))
        width = src_width if width is None else width
        height = src_height if height is None else height
        gc = self._graphics_context()
        gc.DrawBitmap(wx.Bitmap(source), x, y, width, height)

    def _graphics_context(self):
        gc = wx.GraphicsContext.Create(self.dc)
        for region in self._clips:
            gc.Clip(region)
        return gc

    def _restore_clip(self):
        self.dc.DestroyClippingRegion()
        for region in self._clips:
            self.dc.SetDeviceClippingRegion(region)

    def clipRect(self, x, y, width, height):
        self.clipRegion(wx.Region(int(x), int(y), max(0, int(width)), max(0, int(height))))

    def clipRegion(self, region):
        """wx-only native Region clip; no path-to-region approximation."""
        self._clips.append(wx.Region(region))
        self._restore_clip()

    def clipPath(self, path, fillRule=FillRule.NonZero):
        path_commands(path)
        fill_rule(fillRule)
        raise NotImplementedError('wx exposes rectangle/Region clipping, not GraphicsPath clipping')

    def drawPath(self, path, fill=None, stroke=None, width=1, fillRule=FillRule.NonZero):
        commands, rule = path_commands(path), fill_rule(fillRule)
        gc = self._graphics_context()
        native = gc.CreatePath()
        for op, *values in commands:
            if op == 'Z': native.CloseSubpath()
            else: getattr(native, {'M':'MoveToPoint', 'L':'AddLineToPoint',
                                  'Q':'AddQuadCurveToPoint', 'C':'AddCurveToPoint'}[op])(*values)
        if fill is not None:
            gc.SetBrush(self._brush(fill))
            gc.FillPath(native, wx.WINDING_RULE if rule == 'nonzero' else wx.ODDEVEN_RULE)
        if stroke is not None:
            pen = wx.GraphicsPenInfo(int_to_wx_colour(stroke)).Width(width)
            gc.SetPen(gc.CreatePen(pen))
            gc.StrokePath(native)
