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

class WXBase(PUINode):
    scroll = False
    container_x = False
    container_y = False
    strong_expand_x = False
    strong_expand_y = False
    weak_expand_x = False
    weak_expand_y = False
    nweak_expand_x = False
    nweak_expand_y = False
    strong_expand_x_children = 0
    strong_expand_y_children = 0

    @property
    def expand_x(self):
        return self.strong_expand_x or (self.weak_expand_x and not self.nweak_expand_x)

    @property
    def expand_y(self):
        return self.strong_expand_y or (self.weak_expand_y and not self.nweak_expand_y)

    def update(self, prev):
        parent = self.wxparent
        if parent:
            if not parent.scroll and len(parent.children) == 1:
                if parent.expand_x:
                    self.strong_expand_x = True
                if parent.expand_y:
                    self.strong_expand_y = True

            # request expanding from inside
            if parent.container_x:
                if parent.expand_y:
                    self.strong_expand_y = True
                if self.layout_weight:
                    self.strong_expand_x = True
                    parent.strong_expand_x_children += 1
                    p = parent
                    while p:
                        if isinstance(p, WXBase):
                            p.weak_expand_x = True
                        if p==p.parent:
                            break
                        p = p.parent

            if parent.container_y:
                if parent.expand_x:
                    self.strong_expand_x = True
                if self.layout_weight:
                    self.strong_expand_y = True
                    parent.strong_expand_y_children += 1
                    p = parent
                    while p:
                        if isinstance(p, WXBase):
                            p.weak_expand_y = True
                        if p==p.parent:
                            break
                        p = p.parent

            if parent.strong_expand_x_children > 0:
                self.nweak_expand_x = True
            if parent.strong_expand_y_children > 0:
                self.nweak_expand_y = True

        else:
            # mark root node as expanding
            self.strong_expand_x = True
            self.strong_expand_y = True

        super().update(prev)

    @property
    def wxparent(self):
        parent = self.parent
        while not isinstance(parent, WXBase):
            if parent==parent.parent:
                parent = None
                break
            parent = parent.parent
        return parent


class WxBaseWidget(WXBase):
    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.layout_padding = (3, 3, 3, 3)

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
        if self.ui is not None:
            self.ui.Destroy()
            self.ui = None
        super().destroy(direct)

class WxBaseLayout(WXBase):
    def __init__(self):
        super().__init__()
        if not isinstance(self.non_virtual_parent, WxBaseLayout):
            self.layout_padding = (11,11,11,11)

    def destroy(self, direct):
        # self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def addChild(self, idx, child):
        from .layout import Spacer
        weight = child.layout_weight
        if weight is None:
            weight = 0
        if not weight and self.container_x and child.expand_x:
            weight = 1
        if not weight and self.container_y and child.expand_y:
            weight = 1
        flag = wx.ALL

        p = 0
        if child.layout_padding:
            p = max(child.layout_padding)
        if isinstance(child, WxBaseLayout):
            self.ui.Insert(idx, child.outer, proportion=weight, flag=flag|wx.EXPAND, border=p)
        elif isinstance(child, WxBaseWidget):
            if child.expand_x or child.expand_y or child.weak_expand_x or child.weak_expand_y:
                flag |= wx.EXPAND
            else:
                flag |= wx.ALIGN_CENTER
            self.ui.Insert(idx, child.outer, proportion=weight, flag=flag, border=p)
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

    def postSync(self):
        if self.ui:
            self.ui.Layout()
            self.ui.Fit(getWindow(self.parent))
        super().postSync()
