from .. import *
from .base import *
from .menu import *

class QtModal(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        # Escape calls reject() without closeEvent(). Resolve the current node
        # when signalled, since this dialog survives declarative updates.
        self.rejected.connect(self._rejected)

    def _rejected(self):
        self.puinode._close()

    def closeEvent(self, arg__1) -> None:
        self.puinode._close()
        return super().closeEvent(arg__1)

class Modal(QtWindowState, QtBaseWidget):
    pui_terminal = False
    pui_outoforder = True

    def __init__(self, status, offValue=None, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.status = status
        self.offValue = offValue
        self.title = title
        self.preferred_size = size
        self._initial_maximize = maximize
        self._initial_fullscreen = fullscreen
        self.open_cb = None
        self.close_cb = None

    @property
    def outer(self):
        return self.ui

    @property
    def inner(self):
        return self.layout

    def destroy(self, direct):
        self.close_modal()
        super().destroy(direct)

    def update(self, prev=None):
        creating = not (prev and prev.ui)
        if prev and prev.ui:
            self.layout = prev.layout
            self.ui = prev.ui
            self.curr_size = prev.curr_size
            self.curr_status = prev.curr_status
        else:
            self.ui = QtModal()
            self.ui.setModal(True)
            self.layout = QtWidgets.QVBoxLayout()
            self.ui.setLayout(self.layout)
            self.layout.setContentsMargins(0,0,0,0)
            self.curr_size = Prop()
            self.curr_status = Prop(False)

        if self.curr_size.set(self.preferred_size) and self.preferred_size is not None:
            self.ui.resize(*self.preferred_size)
        if creating:
            self._apply_initial_window_state()
        if not self.title is None:
            self.ui.setWindowTitle(self.title)

        self.ui.puinode = self

        if self.status.value:
            self.open_modal()
        else:
            self.close_modal()
        super().update(prev)

    def open(self, cb, *args, **kwargs):
        self.open_cb = (cb, args, kwargs)
        return self

    def close(self, cb, *args, **kwargs):
        self.close_cb = (cb, args, kwargs)
        return self

    def open_modal(self):
        if self.curr_status.set(True):
            self.ui.show()
            if self.open_cb:
                self.open_cb[0](*self.open_cb[1], **self.open_cb[2])

    def close_modal(self):
        if self.curr_status.set(False):
            self.ui.close()
            if self.close_cb:
                self.close_cb[0](*self.close_cb[1], **self.close_cb[2])

    def _close(self, *args, **kwargs):
        node = self.get_node()
        node.close_modal()
        node.status.value = node.offValue

    def addChild(self, idx, child):
        from .layout import Spacer
        if isinstance(child, MenuBar):
            self.ui.setMenuBar(child.outer)
        elif isinstance(child, Spacer):
            self.layout.insertItem(idx, child.outer)
        elif isinstance(child, Modal):
            child.outer.show()
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.layout.insertWidget(idx, child.outer, **params)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        from .layout import Spacer
        if isinstance(child, MenuBar):
            child.outer.close()
        elif isinstance(child, Spacer):
            self.layout.removeItem(child.outer)
        elif isinstance(child, Modal):
            child.outer.close()
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])
