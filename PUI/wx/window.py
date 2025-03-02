from .. import *
from .base import *

class Window(WxBaseWidget):
    pui_terminal = False

    def __init__(self, title=None, icon=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.icon = icon
        self.size = size
        self.curr_icon = None
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_icon = prev.curr_icon
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            self.ui = wx.Frame(None)
            self.curr_icon = Prop()
            self.curr_size = Prop()
            self.curr_maximize = Prop()
            self.curr_fullscreen = Prop()

        if self.curr_icon.set(self.icon):
            self.ui.SetIcon(wx.Icon(self.icon))
        if self.curr_size.set(self.size):
            self.ui.SetSize(wx.Size(*self.size))
        if self.curr_maximize.set(self.maximize):
            self.ui.Maximize(True)
        if self.curr_fullscreen.set(self.fullscreen):
            self.ui.ShowFullScreen(True)
        if not self.title is None:
            self.ui.SetTitle(self.title)
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

    def postSync(self):
        self.ui.Layout()
