"""Non-grabbing suggestions; the native combo keeps keyboard focus."""
import wx
from ..common import combobox_matches


class Completion:
    def __init__(self, node):
        self.node = node
        self.closed = False
        self.geometry_pending = False
        self.geometry = None
        self.popup = wx.PopupWindow(node.ui)
        self.rows = wx.ListBox(self.popup)
        layout = wx.BoxSizer(wx.VERTICAL)
        layout.Add(self.rows, 1, wx.EXPAND)
        self.popup.SetSizer(layout)
        self.geometry_windows = []
        window = node.ui
        while window:
            self.geometry_windows.append(window)
            window.Bind(wx.EVT_MOVE, self.geometry_event)
            window.Bind(wx.EVT_SIZE, self.geometry_event)
            if window.IsTopLevel():
                break
            window = window.GetParent()
        self.indices = []
        self.signature = None
        self.rows.Bind(wx.EVT_LEFT_UP, self.select)
        self.rows.Bind(wx.EVT_KILL_FOCUS, self.blur)
        node.ui.Bind(wx.EVT_KEY_DOWN, self.key)
        node.ui.Bind(wx.EVT_KILL_FOCUS, self.blur)
        node.ui.Bind(wx.EVT_COMBOBOX_DROPDOWN, self.hide_event)
        node.ui.Bind(wx.EVT_IDLE, self.idle_geometry)

    def refresh(self, show=False):
        node = self.node
        if node.destroyed or not node.editable or not node.autoexpand or node.disabled:
            self.popup.Hide()
            return
        opened = self.popup.IsShown()
        if not show and not opened:
            return
        self.indices = combobox_matches([c.text for c in node.children], node.ui.GetValue())
        signature = [(i, node.children[i].key, str(node.children[i].text)) for i in self.indices]
        if show or signature != self.signature:
            self.rows.Set([str(node.children[i].text) for i in self.indices])
            self.signature = signature
        self.position()
        self.popup.Show(bool(self.indices))

    def position(self):
        node = self.node
        font = node.ui.GetFont()
        if self.rows.GetFont() != font:
            self.rows.SetFont(font)
        height = min(8, len(self.indices)) * (self.rows.GetCharHeight() + 8) + 4
        size = (node.ui.GetSize().width, max(24, height))
        origin = tuple(node.ui.ClientToScreen((0, 0)))
        geometry = (size, origin, node.ui.GetSize().height)
        if geometry != self.geometry:
            self.popup.SetSize(size)
            self.popup.Position(wx.Point(*origin), wx.Size(0, geometry[2]))
            self.geometry = geometry

    def select(self, event=None):
        row = self.rows.GetSelection()
        if row == wx.NOT_FOUND or row >= len(self.indices):
            return
        node = self.node
        index = self.indices[row]
        self.popup.Hide()
        node.ui.SetSelection(index)
        node._combobox()
        node.ui.SetFocus()
        node.ui.SetInsertionPointEnd()

    def key(self, event):
        if not self.popup.IsShown():
            event.Skip()
            return
        code = event.GetKeyCode()
        if code in (wx.WXK_UP, wx.WXK_DOWN) and self.indices:
            step = 1 if code == wx.WXK_DOWN else -1
            selected = self.rows.GetSelection()
            self.rows.SetSelection((selected + step) % len(self.indices) if selected >= 0 else (0 if step == 1 else len(self.indices)-1))
        elif code == wx.WXK_RETURN and self.rows.GetSelection() != wx.NOT_FOUND:
            self.select()
        elif code == wx.WXK_ESCAPE:
            self.popup.Hide()
        else:
            if code == wx.WXK_TAB:
                self.popup.Hide()
            event.Skip()

    def blur(self, event):
        def check():
            if not self.closed and not self.node.destroyed and wx.Window.FindFocus() not in (self.node.ui, self.rows):
                self.popup.Hide()
        wx.CallAfter(check)
        event.Skip()

    def hide_event(self, event):
        if not self.closed:
            self.popup.Hide()
        event.Skip()

    def geometry_event(self, event):
        # Native sizers finish layout after the size handler returns. Ancestor
        # movement also changes screen coordinates without moving the combo
        # relative to its own parent.
        if not self.closed and self.popup.IsShown() and not self.geometry_pending:
            self.geometry_pending = True
            wx.CallAfter(self.refresh_geometry)
        event.Skip()

    def refresh_geometry(self):
        self.geometry_pending = False
        if not self.closed:
            self.refresh()

    def idle_geometry(self, event):
        # GTK can apply screen-coordinate changes after the queued size work.
        # Only reposition when geometry actually changes; no polling timer.
        if not self.closed and self.popup.IsShown():
            self.position()
        event.Skip()

    def destroy(self):
        self.closed = True
        if self.node.ui:
            for event, handler in ((wx.EVT_KEY_DOWN, self.key), (wx.EVT_KILL_FOCUS, self.blur),
                                   (wx.EVT_IDLE, self.idle_geometry),
                                   (wx.EVT_COMBOBOX_DROPDOWN, self.hide_event)):
                self.node.ui.Unbind(event, handler=handler)
        for window in self.geometry_windows:
            if window:
                window.Unbind(wx.EVT_MOVE, handler=self.geometry_event)
                window.Unbind(wx.EVT_SIZE, handler=self.geometry_event)
        self.geometry_windows.clear()
        if self.popup:
            self.popup.Destroy()
