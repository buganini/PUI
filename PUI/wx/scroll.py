from .. import *
from .base import *
import wx.lib.scrolledpanel as scrolled

class Scroll(WxBaseWidget):
    pui_terminal = False
    weak_expand_x = True
    weak_expand_y = True
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
