from .. import *
from .base import *
import math

class Canvas(WxBaseWidget):
    weak_expand_x = True
    weak_expand_y = True

    def __init__(self, painter, *args):
        super().__init__()
        self.ui = None
        self.painter = painter
        self.args = args

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.Refresh()
        else:
            self.ui = wx.Panel(getWindow(self.parent))
            self.ui.Bind(wx.EVT_PAINT, self._paint)
            self.ui.Bind(wx.EVT_LEFT_DCLICK, self._LeftDblClick)
            self.ui.Bind(wx.EVT_LEFT_DOWN, self._LeftDown)
            self.ui.Bind(wx.EVT_LEFT_UP, self._LeftUp)
            self.ui.Bind(wx.EVT_MOTION, self._Motion)
            self.ui.Bind(wx.EVT_MOUSEWHEEL, self._MouseWheel)
            self.ui.SetMinSize((self.layout_width, self.layout_height))

        super().update(prev)

    def _MouseWheel(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
            e.h_delta = 0
            e.v_delta = event.GetWheelRotation()
            e.x_delta = 0
            e.y_delta = event.GetWheelDelta()
        else:
            e.h_delta = event.GetWheelRotation()
            e.v_delta = 0
            e.x_delta = event.GetWheelDelta()
            e.y_delta = 0
        self.get_node()._wheel(e)

    def _LeftDblClick(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._dblclicked(e)

    def _LeftDown(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._mousedown(e)

    def _LeftUp(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._mouseup(e)

    def _Motion(self, event):
        e = PUIEvent()
        e.x, e.y = event.GetPosition()
        self.get_node()._mousemove(e)

    def _paint(self, event):
        node = self.get_node()

        node.dc = wx.PaintDC(node.ui)
        if not node.style_bgcolor is None:
            original_brush = node.dc.GetBrush()
            node.dc.SetBrush(wx.Brush(int_to_wx_colour(node.style_bgcolor)))
            node.dc.DrawRectangle(self.ui.GetClientRect())
            node.dc.SetBrush(original_brush)

        node.painter(node, *node.args)
        node.dc = None


    def drawText(self, x, y, text, w=None, h=None, size=12, color=None, rotate=0, anchor=Anchor.LEFT_TOP):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        lines = text.split("\n")
        extents = [self.dc.GetTextExtent(l) for l in lines]
        width = max([e[0] for e in extents])
        height = sum([e[1] for e in extents])

        dx = 0
        dy = 0
        if anchor.value[0]=="center":
            dx = width/2
        elif anchor.value[0]=="right":
            dx = width

        if anchor.value[1]=="center":
            dy = height/2
        elif anchor.value[1]=="bottom":
            dy = height

        gc = wx.GraphicsContext.Create(self.dc)

        gc.PushState()

        gc.Translate(x+dx, y+dy)
        gc.Rotate(math.radians(rotate))
        gc.Translate(-dx, -dy)

        if color is None:
            color = self.ui.GetForegroundColour()
        else:
            color = int_to_wx_colour(color)

        gc.SetFont(wx.Font(size, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL), color)
        y_off = 0
        for i,line in enumerate(lines):
            gc.PushState()
            gc.DrawText(line, 0, y_off)
            gc.PopState()
            y_off += extents[i][1]

        gc.PopState()

        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawLine(self, x1, y1, x2, y2, color=0, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        self.dc.SetPen(wx.Pen(int_to_wx_colour(color), width))
        self.dc.DrawLine(int(x1), int(y1), int(x2), int(y2))
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawPolyline(self, coords, color=0, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if color is not None:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(color), width))

        coords = [(int(c[0]), int(c[1])) for c in coords]
        self.dc.DrawLines(coords)

        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is None:
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        else:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is None:
            self.dc.SetPen(wx.NullPen)
        else:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        coords = [(int(c[0]), int(c[1])) for c in coords]
        self.dc.DrawPolygon(coords)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is None:
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        else:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is None:
            self.dc.SetPen(wx.NullPen)
        else:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        x = min(x1, x1)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        self.dc.DrawRectangle(int(x), int(y), int(w), int(h))
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is None:
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        else:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is None:
            self.dc.SetPen(wx.NullPen)
        else:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        self.dc.DrawEllipse(int(x-rx), int(y-ry), int(rx*2), int(ry*2))
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawShapely(self, shape, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is None:
            self.dc.SetBrush(wx.TRANSPARENT_BRUSH)
        else:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is None:
            self.dc.SetPen(wx.NullPen)
        else:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        self._drawShapely(shape, fill, stroke, width)

    def _drawShapely(self, shape, fill=None, stroke=None, width=1):
        if hasattr(shape, "geoms"):
            for g in shape.geoms:
                self.drawShapely(g, fill, stroke, width)
        elif hasattr(shape, "exterior"): # polygon
            gc = wx.GraphicsContext.Create(self.dc)
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

                if fill is not None:
                    gc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
                if stroke is not None:
                    gc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

                gc.DrawPath(path)
        elif hasattr(shape, "x") and hasattr(shape, "y"): # point
            self.drawEllipse(shape.x, shape.y, width/2, width/2, fill=stroke)
        elif hasattr(shape, "coords"): # linestring, linearring
            self.drawPolyline(shape.coords, color=stroke, width=width)
        else:
            raise RuntimeError(f"Not implemented: drawShapely({type(shape).__name__}) {dir(shape)}")