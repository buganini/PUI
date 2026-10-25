from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .base import WxBaseWidget, getWindow, wx


class TextEdit(TextEditBinding, WxBaseWidget):
    expand_x_prio = expand_y_prio = 4

    def __init__(
        self,
        model: _t.Binding[_t.Any],
        edit_model: _t.Binding[_t.Any] | None = None,
        *,
        placeholder: str | None = None,
        readonly: bool = False,
        wrap: bool = True,
    ) -> None:
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.placeholder = placeholder
        self.readonly = readonly
        self.wrap = wrap
        self.editing = False

    def _set_text(self, value):
        if self.ui.GetValue() != value:
            self.ui.ChangeValue(value)

    def update(self, prev):
        style = wx.TE_MULTILINE | (0 if self.wrap else wx.TE_DONTWRAP)
        if prev is not None:
            self.ui = prev.ui
            self.ui.Unbind(wx.EVT_TEXT)
            self.ui.Unbind(wx.EVT_KILL_FOCUS)
            if prev.wrap != self.wrap:
                self.ui.SetWindowStyleFlag(style)
        else:
            self.ui = wx.TextCtrl(getWindow(self.parent), style=style)
        self.ui.SetEditable(not self.readonly)
        self.ui.SetHint(self.placeholder or '')
        self._sync_text(prev)
        self.ui.Bind(wx.EVT_TEXT, self._edited)
        self.ui.Bind(wx.EVT_KILL_FOCUS, self._blurred)
        super().update(prev)

    def _edited(self, event):
        node = self.get_node()
        if not node.destroyed and node.ui is not None:
            node._input_text(node.ui.GetValue())
        event.Skip()

    def _blurred(self, event):
        node = self.get_node()
        if not node.destroyed and node.ui is not None:
            node._commit_text(node.ui.GetValue())
        event.Skip()
