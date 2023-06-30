from .. import *
from .base import *
from .menu import *

class QtModal(QtWidgets.QDialog):
    def closeEvent(self, arg__1) -> None:
        self.puinode._close()
        return super().closeEvent(arg__1)

class Modal(QtBaseWidget):
    terminal = False
    outoforder = True

    def __init__(self, status, offValue=None, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.status = status
        self.offValue = offValue
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None
        self.curr_status = None
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
        return super().destroy(direct)

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
            self.curr_status = prev.curr_status
        else:
            self.ui = QtModal()
            self.ui.setModal(True)
            self.layout = QtWidgets.QVBoxLayout()
            self.ui.setLayout(self.layout)
            self.layout.setContentsMargins(0,0,0,0)

        if self.curr_size != self.size:
            self.curr_size = self.size
            self.ui.resize(*self.size)
        if self.curr_maximize !=  self.maximize:
            self.curr_maximize = self.maximize
            self.ui.showMaximized()
        if self.curr_fullscreen != self.fullscreen:
            self.curr_fullscreen = self.fullscreen
            self.ui.showFullScreen()
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
        if not self.curr_status:
            self.ui.show()
            self.curr_status = True
            if self.open_cb:
                self.open_cb[0](*self.open_cb[1], **self.open_cb[2])

    def close_modal(self):
        prev_status = self.curr_status
        if self.curr_status is None or self.curr_status:
            self.curr_status = False
        if prev_status:
            self.ui.close()
            if self.close_cb:
                self.close_cb[0](*self.close_cb[1], **self.close_cb[2])

    def _close(self, *args, **kwargs):
        node = self.get_node()
        if node.curr_status:
            node.curr_status = False
            if node.close_cb:
                node.close_cb[0](*node.close_cb[1], **node.close_cb[2])
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
