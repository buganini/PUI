from .. import *

import wx

def int_to_wx_colour(color_int):
    red = (color_int >> 16) & 0xFF
    green = (color_int >> 8) & 0xFF
    blue = color_int & 0xFF
    return wx.Colour(red, green, blue)

def getWindow(n):
    from .window import Window
    from .scroll import Scroll
    p = n
    while p:
        if isinstance(p, Scroll):
            return p.ui
        if isinstance(p, Window):
            return p.ui
        p = p.parent
    raise RuntimeError("!!! getWindow returns None for", n.key if n else None)

class WxPUIView(PUIView):
    pui_virtual = True
    def __init__(self):
        super().__init__()

    def destroy(self, direct):
        if self.ui: # PUIView doesn't have ui
            self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def redraw(self):
        wx.CallAfter(self.sync)

    def update(self, prev=None):
        if self.retired_by:
            return
        self.dirty = False
        super().update(prev)
        self.updating = False
        if self.dirty:
            self.update(prev)

class WxBaseWidget(PUINode):
    pui_terminal = True

    def __init__(self):
        super().__init__()

    def update(self, prev):
        super().update(prev)

        if self.style_fontsize:
            font = self.ui.GetFont()
            font.SetPointSize(self.style_fontsize)
            self.ui.SetFont(font)

        # Set font color if specified
        if self.style_color:
            self.ui.SetForegroundColour(int_to_wx_colour(self.style_color))

    def destroy(self, direct):
        self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

class WxBaseLayout(PUINode):
    def __init__(self):
        super().__init__()

    def destroy(self, direct):
        # self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def addChild(self, idx, child):
        from .layout import Spacer
        weight = child.layout_weight
        if weight is None:
            weight = 0
        flag = wx.EXPAND|wx.ALL
        if isinstance(child, WxBaseLayout):
            self.ui.Insert(idx, child.outer, weight, flag)
        elif isinstance(child, WxBaseWidget):
            self.ui.Insert(idx, child.outer, weight, flag)
        elif isinstance(child, Spacer):
            self.ui.InsertStretchSpacer(idx, weight)

    def removeChild(self, idx, child):
        from .layout import Spacer
        if isinstance(child, WxBaseLayout):
            self.ui.Detach(idx)
        elif isinstance(child, WxBaseWidget):
            self.ui.Detach(idx)
        elif isinstance(child, Spacer):
            self.ui.Detach(idx)
