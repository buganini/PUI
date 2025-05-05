from .. import *
from .base import *
import wx.lib.scrolledpanel as scrolled

class Scroll(WxBaseWidget):
    pui_terminal = False
    scroll = True

    END = -0.0

    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = scrolled.ScrolledPanel(getWindow(self.parent))

        self.container_y = True
        self.expand_y_prio = 3
        if self.vertical is False:
            self.container_y = False
            self.expand_y_prio = 1

        self.container_x = True
        self.expand_x_prio = 3
        if self.horizontal is False:
            self.container_x = False
            self.expand_x_prio = 1

        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, WxBaseLayout):
            self.ui.SetSizer(child.outer)
        elif isinstance(child, WxBaseWidget):
            pass

    def removeChild(self, idx, child):
        if isinstance(child, WxBaseLayout):
            pass
        elif isinstance(child, WxBaseWidget):
            pass

    def scrollX(self, pos=0):
        return self

    def scrollY(self, pos=0):
        return self

    def postSync(self):
        self.ui.SetupScrolling(scroll_x=self.horizontal or self.horizontal is None, scroll_y=self.vertical or self.vertical is None, scrollToTop=False)
