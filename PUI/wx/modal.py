from .base import WxSingleChild, getWindow, wx
from .._modal import ModalMixin


class _ModalWindows:
    """One application-wide stack; restore only windows disabled by this stack."""
    def __init__(self, app):
        self.app = app
        self.stack = []
        self.disabled = []

    def refresh(self, event=None):
        self.stack[:] = [window for window in self.stack if window and window.IsShown()]
        top = self.stack[-1] if self.stack else None
        for window in self.disabled[:]:
            if not window or top is None or window is top or not window.IsShown():
                self.disabled.remove(window)
                if window:
                    window.Enable(True)
        if top is not None:
            for window in wx.GetTopLevelWindows():
                if window is not top and window.IsShown() and window.IsEnabled():
                    window.Enable(False)
                    self.disabled.append(window)
        if event is not None:
            event.Skip()

    def open(self, window):
        if not self.stack:
            self.app.Bind(wx.EVT_IDLE, self.refresh)
        # PUI finalizes descendants first. Insert a newly opened parent below
        # already-open descendants, regardless of reconciliation order.
        index = len(self.stack)
        for i, candidate in enumerate(self.stack):
            parent = candidate.GetParent()
            while parent:
                if parent is window:
                    index = min(index, i)
                    break
                parent = parent.GetParent()
        self.stack.insert(index, window)
        self.refresh()

    def close(self, window):
        if window in self.stack:
            self.stack.remove(window)
        self.refresh()
        if not self.stack:
            self.app.Unbind(wx.EVT_IDLE, handler=self.refresh)


class Modal(ModalMixin, WxSingleChild):
    def update(self, prev):
        if prev is not None:
            self.ui, self._native = prev.ui, prev._native
        else:
            owner = wx.GetTopLevelParent(getWindow(self.parent))
            self.ui = wx.Dialog(owner, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
            app = wx.GetApp()
            if not hasattr(app, '_pui_modal_windows'):
                app._pui_modal_windows = _ModalWindows(app)
            self._native = {'manager': app._pui_modal_windows, 'focus': None, 'sized': False}
            self.ui.Bind(wx.EVT_CLOSE, lambda event, ui=self.ui: ui.pui_node._on_close(event))
            self.ui.Bind(wx.EVT_CHAR_HOOK, lambda event, ui=self.ui: ui.pui_node._on_key(event))
            self.ui.Bind(wx.EVT_WINDOW_DESTROY, lambda event, ui=self.ui: ui.pui_node._on_destroy(event))
        self.ui.SetTitle(self.title or '')
        super().update(prev)

    def _on_close(self, event):
        node = self.ui.pui_node
        node._dismiss()
        if event.CanVeto():
            event.Veto()
        else:
            event.Skip()

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.ui.pui_node._dismiss()
        else:
            event.Skip()

    def _on_destroy(self, event):
        if event.GetEventObject() is self.ui:
            node = self.ui.pui_node
            node._native['manager'].close(self.ui)
            node._transition(False)
            node.ui = None
        event.Skip()

    def _set_modal(self, opened):
        if not self.ui or self._modal_state['open'] == opened:
            return
        manager = self._native['manager']
        if opened:
            self._native['focus'] = wx.Window.FindFocus()
            self.ui.Show()
            manager.open(self.ui)
            manager.stack[-1].Raise()
            manager.stack[-1].SetFocus()
        else:
            self.ui.Hide()
            manager.close(self.ui)
            focus = self._native['focus']
            if focus and focus.IsShownOnScreen() and focus.IsEnabled():
                focus.SetFocus()
        self._transition(opened)

    def postSync(self):
        super().postSync()
        if not self._native['sized']:
            if self.preferred_size is None:
                self.ui.Fit()
            else:
                self.ui.SetSize(self.preferred_size)
            if self._initial_maximize is not None:
                self.ui.Maximize(bool(self._initial_maximize))
            if self._initial_fullscreen is not None:
                self.ui.ShowFullScreen(bool(self._initial_fullscreen))
            self._native['sized'] = True
        self._native['manager'].refresh()
