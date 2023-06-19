from .. import *
from .base import *
from PySide6.QtWidgets import QSizePolicy

class Scroll(QtBaseWidget):
    terminal = False

    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QScrollArea()
            self.ui.setWidgetResizable(True)
            if self.vertical is None:
                self.ui.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            elif self.vertical:
                self.ui.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            else:
                self.ui.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            if self.horizontal is None:
                self.ui.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            elif self.horizontal:
                self.ui.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
            else:
                self.ui.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.setWidget(child.outer)
            if not hasattr(child.outer, "origResizeEvent"):
                child.outer.origResizeEvent = child.outer.resizeEvent
            child.outer.resizeEvent = self.onUiResized
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])

    def onUiResized(self, event):
        node = self.get_node()
        if node.destroyed:
            return
        node.children[0].outer.origResizeEvent(event)
        node.children[0].outer.resizeEvent = self.onUiResized
        if node.horizontal is False:
            if isinstance(node.children[0], QtBaseLayout):
                node.outer.setMinimumWidth(node.children[0].outer.sizeHint().width())
            elif isinstance(node.children[0], QtBaseWidget):
                node.outer.setMinimumWidth(node.children[0].outer.sizeHint().width())

        if node.vertical is False:
            if isinstance(node.children[0], QtBaseLayout):
                node.outer.setMinimumHeight(node.children[0].outer.sizeHint().height())
            elif isinstance(node.children[0], QtBaseWidget):
                self.outer.setMinimumHeight(node.children[0].outer.sizeHint().height())
