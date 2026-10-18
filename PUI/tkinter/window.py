from ..refs import NodeBinder as _NodeBinder
from .. import *
from .base import *

class _WindowBinder(_NodeBinder):
    def maximize(self, enabled: bool):
        self._schedule(enabled, self._maximize)

    def _maximize(self, node, enabled):
        ui = node.ui
        minimized = ui.state() == 'iconic'
        try:
            ui.attributes('-zoomed', enabled)
        except tk.TclError:
            ui.state('zoomed' if enabled else 'normal')
        if minimized:
            ui.iconify()

    def minimize(self, enabled: bool):
        self._schedule(enabled, self._minimize)

    def _minimize(self, node, enabled):
        ui = node.ui
        if enabled:
            ui.iconify()
        else:
            ui.deiconify()

    def fullscreen(self, enabled: bool):
        self._schedule(enabled, self._fullscreen)

    def _fullscreen(self, node, enabled):
        ui = node.ui
        minimized = ui.state() == 'iconic'
        ui.attributes('-fullscreen', enabled)
        if minimized:
            ui.iconify()


class Window(TkBaseWidget):
    def __pui_binder__(self):
        return _WindowBinder(self, self.get_poster())

    pui_terminal = False
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self._initial_maximize = maximize
        self._initial_fullscreen = fullscreen

    def update(self, prev):
        creating = not (prev and prev.ui is not None)
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_size = prev.curr_size
        else:
            self.ui = tk.Toplevel(self.tkparent.inner)
            application = self
            while application.parent is not application:
                application = application.parent
            application._register_window(self.ui)
            self.curr_size = Prop()

        if self.curr_size.set(self.size) and self.size is not None:
            self.ui.geometry("x".join([str(v) for v in self.size]))

        if creating:
            if self._initial_maximize is not None:
                try:
                    self.ui.attributes('-zoomed', bool(self._initial_maximize))
                except tk.TclError:
                    self.ui.state('zoomed' if self._initial_maximize else 'normal')
            if self._initial_fullscreen is not None:
                self.ui.attributes('-fullscreen', bool(self._initial_fullscreen))

        title = window_title(self)
        if title is not None:
            self.ui.title(title)
        super().update(prev)

    def maximize(self, enabled=True):
        self._initial_maximize = enabled
        return self

    def fullscreen(self, enabled=True):
        self._initial_fullscreen = enabled
        return self

    def addChild(self, idx, child):
        if idx:
            return
        child.outer.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        child.outer.pack_forget()

    def postSync(self):
        if self.children:
            child = self.children[0]
            if child._visible:
                child.outer.pack(fill=tk.BOTH, expand=True)
            else:
                child.outer.pack_forget()
        super().postSync()
