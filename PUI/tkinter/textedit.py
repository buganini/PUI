from __future__ import annotations
from .. import _typing as _t
from .._textedit import TextEditBinding
from .base import TkBaseWidget, tk


class TextEdit(TextEditBinding, TkBaseWidget):
    expand_x_prio = expand_y_prio = 4
    grid_sticky = 'nsew'

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
        self.event_bindings = {}

    def _value(self):
        return self.ui.get('1.0', 'end-1c')

    def _set_text(self, value):
        if self._value() != value:
            self.ui.configure(state='normal')
            self.ui.delete('1.0', 'end')
            self.ui.insert('1.0', value)
            self.ui.edit_modified(False)
            self.ui.configure(state='disabled' if self.readonly else 'normal')
        self._show_hint()

    def _show_hint(self):
        self.hint.configure(text=self.placeholder or '', font=self.ui.cget('font'),
                            background=self.ui.cget('background'))
        if self.placeholder and not self._value():
            self.hint.place(x=4, y=3)
        else:
            self.hint.place_forget()

    def update(self, prev):
        if prev is not None:
            self.ui, self.hint = prev.ui, prev.hint
            for sequence, binding in prev.event_bindings.items():
                self.ui.unbind(sequence, binding)
        else:
            self.ui = tk.Text(self.tkparent.inner, undo=True, width=1, height=4)
            self.hint = tk.Label(self.ui, foreground='gray', anchor='nw')
            self.hint.bind('<Button-1>', lambda event: self.ui.focus_set())
        self.ui.configure(wrap='word' if self.wrap else 'none',
                          state='disabled' if self.readonly else 'normal')
        self._sync_text(prev)
        self.event_bindings = {
            '<<Modified>>': self.ui.bind('<<Modified>>', self._edited),
            '<FocusOut>': self.ui.bind('<FocusOut>', self._blurred),
            '<Tab>': self.ui.bind('<Tab>', lambda event: self._focus_next(False)),
            '<Shift-Tab>': self.ui.bind('<Shift-Tab>', lambda event: self._focus_next(True)),
        }
        super().update(prev)
        self._show_hint()

    def _focus_next(self, backwards):
        target = self.ui.tk_focusPrev() if backwards else self.ui.tk_focusNext()
        target.focus_set()
        return 'break'

    def _edited(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or not node.ui.edit_modified():
            return
        node.ui.edit_modified(False)
        node._input_text(node._value())
        node._show_hint()

    def _blurred(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        # Flush a queued <<Modified>> before committing on focus loss.
        node._edited(event)
        node._commit_text(node._value())

    def destroy(self, direct):
        for sequence, binding in self.event_bindings.items():
            try:
                self.ui.unbind(sequence, binding)
            except tk.TclError:
                pass
        self.event_bindings = {}
        super().destroy(direct)
