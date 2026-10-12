from .. import *
from .base import *

class Application(WxPUIView):
    def __init__(self, icon=None):
        super().__init__()
        self.ui = None
        self.icon = icon

    def redraw(self):
        if self.ui:
            super().redraw()
        else:
            self.sync()

    def update(self, prev=None):
        if not self.ui:
            self.ui = wx.GetApp() or wx.App()
            if hasattr(self.ui, "SetMacExitMenuItemId"):
                self.ui.SetMacExitMenuItemId(wx.ID_EXIT)
            self.ui.Bind(wx.EVT_MENU, self.onExit, id=wx.ID_EXIT)

        super().update(prev)

    def addChild(self, idx, child):
        if self.icon and getattr(child, 'icon', None) is None:
            child.outer.SetIcon(wx.Icon(self.icon))
        child.outer.Show()

    def removeChild(self, idx, child):
        child.outer.Close()

    def start(self):
        self.ui.MainLoop()

    def onExit(self, event):
        self.quit()

    def quit(self):
        wx.CallAfter(self._quit)

    def _quit(self):
        for window in wx.GetTopLevelWindows():
            window.Close()

def PUIApp(func):
    def func_wrapper(*args, **kwargs):
        class PUIAppWrapper(Application):
            def __init__(self, name):
                self.name = name
                super().__init__()

            def content(self):
                return func(*args, **kwargs)

        ret = PUIAppWrapper(func.__name__)
        return ret

    return func_wrapper
