from .base import TkBaseWidget, tk
from .._modal import ModalMixin


class Modal(ModalMixin, TkBaseWidget):
    def update(self, prev):
        if prev is not None:
            self.ui, self._native = prev.ui, prev._native
        else:
            owner = self.tkparent.inner.winfo_toplevel()
            self.ui = tk.Toplevel(owner)
            self.ui.withdraw()
            self.ui.transient(owner)
            self._native = {'after': None, 'grab': None, 'focus': None}
            self.ui.protocol('WM_DELETE_WINDOW', lambda widget=self.ui: widget.pui_node._dismiss())
            self.ui.bind('<Escape>', lambda e, widget=self.ui: widget.pui_node._escape(), add='+')
            if self.preferred_size is not None:
                self.ui.geometry('%dx%d' % self.preferred_size)
            if self._initial_fullscreen is not None:
                self.ui.attributes('-fullscreen', bool(self._initial_fullscreen))
            if self._initial_maximize:
                try:
                    self.ui.attributes('-zoomed', True)
                except tk.TclError:
                    self.ui.state('zoomed')
        self.ui.title(self.title or '')
        super().update(prev)

    def _escape(self):
        if self.ui.grab_current() is self.ui:
            self._dismiss()
            return 'break'

    def _take_grab(self):
        node = self.get_node()
        node._native['after'] = None
        if node.destroyed or not node._modal_state['open']:
            return
        if not node.ui.winfo_viewable():
            node._native['after'] = node.ui.after(10, node._take_grab)
            return
        current = node.ui.grab_current()
        # A nested modal already owns input; don't steal its grab.
        if current is not None and str(current).startswith(str(node.ui) + '.'):
            return
        if current is not None and current is not node.ui:
            node._native['grab'] = current
        node.ui.grab_set()
        node.ui.focus_set()

    def _set_modal(self, opened):
        if self.ui is None or self._modal_state['open'] == opened:
            return
        if opened:
            self._native['grab'] = self.ui.grab_current()
            self._native['focus'] = self.ui.focus_get()
            self.ui.deiconify()
            self._native['after'] = self.ui.after_idle(self._take_grab)
        else:
            timer = self._native['after']
            if timer is not None:
                self.ui.after_cancel(timer)
                self._native['after'] = None
            try:
                if self.ui.grab_current() is self.ui:
                    self.ui.grab_release()
                    previous = self._native['grab']
                    if previous is not None and previous.winfo_exists() and previous.winfo_viewable():
                        previous.grab_set()
                self.ui.withdraw()
                focus = self._native['focus']
                if focus is not None and focus.winfo_exists() and focus.winfo_viewable():
                    focus.focus_set()
            except tk.TclError:
                pass
        self._transition(opened)

    def addChild(self, idx, child):
        child.outer.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        child.outer.pack_forget()
