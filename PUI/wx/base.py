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
    container_x = False # axis
    container_y = False # axis
    expand_x_prio = 0
    expand_y_prio = 0
    expand_x1_children = 0
    expand_x2_children = 0
    expand_x3_children = 0
    expand_x4_children = 0
    expand_y1_children = 0
    expand_y2_children = 0
    expand_y3_children = 0
    expand_y4_children = 0
    cached_wxparent = None

    @property
    def expand_x(self):
        return self.expand_x_prio

    @property
    def expand_y(self):
        return self.expand_y_prio

    def update(self, prev):
        self.cached_wxparent = parent = self.wxparent

        parent = self.wxparent
        if parent:
            if self.layout_weight:
                if parent.container_x:
                    self.expand_x_prio = 4
                if parent.container_y:
                    self.expand_y_prio = 4

            if self.expand_x_prio >= 1:
                parent.expand_x1_children += 1
            if self.expand_x_prio >= 2:
                parent.expand_x2_children += 1
            if self.expand_x_prio >= 3:
                parent.expand_x3_children += 1
            if self.expand_x_prio >= 4:
                parent.expand_x4_children += 1

            if self.expand_y_prio >= 1:
                parent.expand_y1_children += 1
            if self.expand_y_prio >= 2:
                parent.expand_y2_children += 1
            if self.expand_y_prio >= 3:
                parent.expand_y3_children += 1
            if self.expand_y_prio >= 4:
                parent.expand_y4_children += 1

        super().update(prev)

    def postUpdate(self):
        parent = self.cached_wxparent
        if parent:
            if parent.container_x:
                if self.expand_x_prio < 1 and parent.expand_x1_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 2 and parent.expand_x2_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 3 and parent.expand_x3_children > 0:
                    self.expand_x_prio = 0
                if self.expand_x_prio < 4 and parent.expand_x4_children > 0:
                    self.expand_x_prio = 0

            if parent.container_y:
                if self.expand_y_prio < 1 and parent.expand_y1_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 2 and parent.expand_y2_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 3 and parent.expand_y3_children > 0:
                    self.expand_y_prio = 0
                if self.expand_y_prio < 4 and parent.expand_y4_children > 0:
                    self.expand_y_prio = 0

        if self._debug:
            print("layout", self.key, f"weight={self.layout_weight}", f"expand_x={self.expand_x}", f"expand_y={self.expand_y}")

        super().postUpdate()

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
        self.relayout = False
        if not isinstance(self.non_virtual_parent, WxBaseLayout):
            self.layout_padding = (11,11,11,11)

    def destroy(self, direct):
        # self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def update(self, prev):
        if prev and prev.ui:
            self.sizerItems = prev.sizerItems
        else:
            self.sizerItems = []
        super().update(prev)

    def postUpdate(self):
        super().postUpdate()

        for child, si in self.sizerItems:
            if child.expand_x or child.expand_y:
                si.SetFlag(wx.ALL | wx.EXPAND)
            else:
                # si.SetFlag(wx.ALL | wx.ALIGN_CENTER)
                si.SetFlag(wx.ALL) # XXX

            weight = child.layout_weight
            if self.container_x and child.expand_x:
                si.SetProportion(weight if weight else 1 if child.expand_x else 0)
            elif self.container_y and child.expand_y:
                si.SetProportion(weight if weight else 1 if child.expand_y else 0)

            p = 0
            if child.layout_padding:
                p = max(child.layout_padding)
            si.SetBorder(p)

    def addChild(self, idx, child):
        from .layout import Spacer
        self.relayout = True

        weight = child.layout_weight
        if weight is None:
            weight = 0
        if not weight and self.container_x and child.expand_x:
            weight = 1
        if not weight and self.container_y and child.expand_y:
            weight = 1

        if isinstance(child, WxBaseLayout):
            si = self.ui.Insert(idx, child.outer)
            self.sizerItems.insert(idx, (child, si))
        elif isinstance(child, WxBaseWidget):
            si = self.ui.Insert(idx, child.outer)
            self.sizerItems.insert(idx, (child, si))
        elif isinstance(child, Spacer):
            si = self.ui.InsertStretchSpacer(idx)
            self.sizerItems.insert(idx, (child, si))

    def removeChild(self, idx, child):
        self.relayout = True

        from .layout import Spacer
        if isinstance(child, WxBaseLayout):
            self.ui.Detach(idx)
            self.sizerItems.pop(idx)
        elif isinstance(child, WxBaseWidget):
            self.ui.Detach(idx)
            self.sizerItems.pop(idx)
        elif isinstance(child, Spacer):
            self.ui.Detach(idx)
            self.sizerItems.pop(idx)

    def postSync(self):
        if self.relayout and self.ui:
            self.relayout = False
            self.ui.Layout()
            # self.ui.Fit(getWindow(self.parent))
        super().postSync()
