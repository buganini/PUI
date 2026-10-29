"""Tk window menus; native integration is selected by Tk's platform backend."""
from .base import *
from .layout import Spacer


class _MenuContainer(PUINode):
    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.items = prev.ui, prev.items
        else:
            parent = self.parent
            while not isinstance(parent.ui, tk.Misc):
                if parent.parent is parent:
                    raise TypeError('Menus require a Tk window or menu parent')
                parent = parent.parent
            self.ui = tk.Menu(parent.ui, tearoff=False)
            self.items = []
        super().update(prev)

    def addChild(self, idx, child):
        if not (isinstance(child, (Menu, MenuAction)) or
                isinstance(self, MenuBar) and isinstance(child, Spacer)):
            raise TypeError('MenuBar accepts Menu, MenuAction or Spacer; Menu accepts Menu or MenuAction')
        self.items.insert(idx, child)

    def removeChild(self, idx, child):
        self.items.pop(idx)

    def postSync(self):
        self.ui.delete(0, tk.END)
        for i, child in enumerate(self.items):
            child = child.get_node()
            self.items[i] = child
            if isinstance(child, Spacer):
                continue
            if isinstance(child, Menu):
                self.ui.add_cascade(label=child.text, menu=child.ui)
            else:
                self.ui.add_command(label=child.text, command=child._triggered)
        super().postSync()

    def destroy(self, direct):
        if direct and self.ui is not None:
            try:
                self.ui.destroy()
            except tk.TclError:
                pass  # The owning window may already have been destroyed.
        self.items = []
        super().destroy(direct)


class MenuBar(_MenuContainer):
    pui_outoforder = True

    def __init__(self, *, native=True):
        super().__init__()
        self.native = native  # Accepted; Tk controls platform integration.


class Menu(_MenuContainer):
    def __init__(self, text):
        super().__init__()
        self.text = text


class MenuAction(PUINode):
    pui_terminal = True

    def __init__(self, text, *, native=True):
        super().__init__()
        self.text, self.native = text, native
        self.onTriggered = None

    def update(self, prev):
        # Tk commands are menu entries, not independent widgets.
        self.ui = prev.ui if prev else object()
        super().update(prev)

    def trigger(self, callback, *args, **kwargs):
        self.onTriggered = callback, args, kwargs
        return self

    def _triggered(self):
        node = self.get_node()
        if not node.destroyed and node.onTriggered:
            callback, args, kwargs = node.onTriggered
            callback(*args, **kwargs)
