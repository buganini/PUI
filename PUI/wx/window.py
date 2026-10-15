from .. import *
from .base import *
from .menu import MenuBar

class Window(WxWindowState, WxSingleChild):
    pui_terminal = False

    def __init__(self, title=None, icon=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.icon = icon
        self.size = size
        self.curr_icon = None
        self.curr_size = None
        self._initial_maximize = maximize
        self._initial_fullscreen = fullscreen

    @property
    def inner(self):
        return self.panel

    def update(self, prev=None):
        creating = not (prev and prev.ui)
        if prev and prev.ui:
            self.ui = prev.ui
            self.panel = prev.panel
            self.close_accelerator_id = prev.close_accelerator_id
            self.ui.Unbind(wx.EVT_MENU, id=self.close_accelerator_id)
            self.ui.Unbind(wx.EVT_MENU, id=wx.ID_EXIT)
            self.ui.Unbind(wx.EVT_CHAR_HOOK, handler=prev.onKey)
            self.curr_icon = prev.curr_icon
            self.curr_size = prev.curr_size
        else:
            self.ui = wx.Frame(None)
            self.panel = wx.Panel(self.ui) # to grab focus when clicked
            frame_sizer = wx.BoxSizer(wx.VERTICAL)
            frame_sizer.Add(self.panel, 1, wx.EXPAND)
            self.ui.SetSizer(frame_sizer)
            self.close_accelerator_id = int(wx.NewIdRef())
            self.ui.SetAcceleratorTable(wx.AcceleratorTable([
                (wx.ACCEL_CMD, ord("Q"), wx.ID_EXIT),
                (wx.ACCEL_ALT, wx.WXK_F4, self.close_accelerator_id),
            ]))
            self.curr_icon = Prop()
            self.curr_size = Prop()

        self.ui.Bind(wx.EVT_CHAR_HOOK, self.onKey)
        self.ui.Bind(wx.EVT_MENU, self.onCloseAccelerator, id=self.close_accelerator_id)
        self.ui.Bind(wx.EVT_MENU, self.onExitAccelerator, id=wx.ID_EXIT)

        if self.curr_icon.set(self.icon) and self.icon is not None:
            self.ui.SetIcon(wx.Icon(self.icon))
        if self.curr_size.set(self.size) and self.size is not None:
            self.ui.SetSize(wx.Size(*self.size))
        if creating:
            if self._initial_maximize is not None:
                self.maximize(self._initial_maximize)
            if self._initial_fullscreen is not None:
                self.fullscreen(self._initial_fullscreen)
        title = window_title(self)
        if title is not None:
            self.ui.SetTitle(title)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, MenuBar):
            self.ui.SetMenuBar(child.ui)
        else:
            super().addChild(idx, child)

    def removeChild(self, idx, child):
        if isinstance(child, MenuBar):
            self.ui.SetMenuBar(None)
        else:
            super().removeChild(idx, child)

    def onKey(self, event):
        e = PUIEvent()
        key = event.GetUnicodeKey()
        e.text = chr(key) if key != wx.WXK_NONE else ''
        self.get_node()._keypress(e)
        event.Skip()

    def postSync(self):
        super().postSync()
        self.ui.Layout()

    def onCloseAccelerator(self, event):
        self.ui.Close()

    def onExitAccelerator(self, event):
        app = wx.GetApp()
        if app:
            for window in wx.GetTopLevelWindows():
                window.Close()
        else:
            self.ui.Close()
