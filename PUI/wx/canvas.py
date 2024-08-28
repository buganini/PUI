from .. import *
from .base import *

def int_to_wx_colour(color_int):
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return wx.Colour(red, green, blue)

class Canvas(WxBaseWidget):
    def __init__(self, painter, *args):
        super().__init__()
        self.ui = None
        self.painter = painter
        self.args = args

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.SetLabel(self.text)
        else:
            self.ui = wx.Panel(getWindow(self.parent))
            self.ui.Bind(wx.EVT_PAINT, self._paint)


        self.ui.SetMinSize((self.layout_width, self.layout_height))

        super().update(prev)

    def _paint(self, *args):
        node = self.get_node()
        node.dc = wx.PaintDC(node.ui)

        if not node.style_bgcolor is None:
            node.dc.SetBrush(wx.Brush(int_to_wx_colour(node.style_bgcolor)))            
            node.dc.DrawRectangle(self.ui.GetClientRect())

        node.painter(node, *node.args)


    def drawText(self, x, y, text, w=None, h=None, rotate=0, anchor=Anchor.LEFT_TOP):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        self.dc.DrawText(text, x, y)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawLine(self, x1, y1, x2, y2, color=0, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        self.dc.SetPen(wx.Pen(int_to_wx_colour(color), width))
        self.dc.DrawLine(x1, y1, x2, y2)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawPolyline(self, coords, color=0, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if color is not None:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(color), width))

        self.dc.DrawLines(coords)

        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawPolygon(self, coords, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is not None:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is not None:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        self.dc.DrawPolygon(coords)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawRect(self, x1, y1, x2, y2, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is not None:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is not None:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        self.dc.DrawRectangle(x1, y1, x2, y2)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)

    def drawEllipse(self, x, y, rx, ry, fill=None, stroke=None, width=1):
        original_pen = self.dc.GetPen()
        original_brush = self.dc.GetBrush()

        if fill is not None:
            self.dc.SetBrush(wx.Brush(int_to_wx_colour(fill)))
        if stroke is not None:
            self.dc.SetPen(wx.Pen(int_to_wx_colour(stroke), width))

        self.dc.DrawEllipse(x, y, rx*2, ry*2)
        self.dc.SetPen(original_pen)
        self.dc.SetBrush(original_brush)