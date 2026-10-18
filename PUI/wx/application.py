from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
from functools import wraps as _wraps
from ..decorator import _warn_deprecated_decorator

class Application(WxPUIView):
    def __init__(self, icon: _t.Any = None, *, title: str = '') -> None:
        super().__init__()
        self.title = title
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

        if self.title:
            self.ui.SetAppDisplayName(self.title)
        super().update(prev)

    def addChild(self, idx, child):
        if self.icon and getattr(child, 'icon', None) is None:
            child.outer.SetIcon(wx.Icon(self.icon))
        child.outer.Show()

    def removeChild(self, idx, child):
        child.outer.Close()

    def run(self, *, codex: _t.AIProvider = None, claude: _t.AIProvider = None, **kwargs):
        if codex is not None:
            kwargs['codex'] = codex
        if claude is not None:
            kwargs['claude'] = claude
        return self.start(**kwargs)

    def start(self, *, landlock=None, codex: _t.AIProvider = None, claude: _t.AIProvider = None):
        from ..ai.native import start
        return start(self, 'wx', lambda: self.ui.MainLoop(), landlock=landlock, codex=codex, claude=claude)

    def onExit(self, event):
        self.quit()

    def quit(self):
        if not self.destroyed and not self.retired_by:
            wx.CallAfter(self._quit)

    def _quit(self):
        if self.destroyed or self.retired_by:
            return
        for window in wx.GetTopLevelWindows():
            window.Close()

def PUIApp(func):
    """Deprecated: subclass Application and implement content() instead."""
    _warn_deprecated_decorator('PUIApp', 'Application')
    @_wraps(func)
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
