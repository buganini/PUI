from .. import *
from .base import *

class Window(TkBaseWidget):
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
                self.maximize(self._initial_maximize)
            if self._initial_fullscreen is not None:
                self.fullscreen(self._initial_fullscreen)

        title = window_title(self)
        if title is not None:
            self.ui.title(title)
        super().update(prev)

    def maximize(self, enabled=True):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node._initial_maximize = enabled
        else:
            try:
                node.ui.attributes('-zoomed', bool(enabled))
            except tk.TclError:
                node.ui.state('zoomed' if enabled else 'normal')
        return self

    def fullscreen(self, enabled=True):
        node = self.get_node()
        if node.destroyed:
            return self
        if node.ui is None:
            node._initial_fullscreen = enabled
        else:
            node.ui.attributes('-fullscreen', bool(enabled))
        return self

    def addChild(self, idx, child):
        if idx:
            return
        child.outer.pack(fill=tk.BOTH, expand=True)

    def removeChild(self, idx, child):
        child.outer.pack_forget()
