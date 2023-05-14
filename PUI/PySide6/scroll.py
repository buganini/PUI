from .. import *
from .base import *
from PySide6.QtWidgets import QSizePolicy

class QtScrollArea(QtBaseWidget):
    terminal = False

    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.widget = None
        super().__init__()

    def destroy(self, direct):
        if direct:
            if self.ui:
                self.ui.deleteLater()
            if self.widget:
                self.widget.deleteLater()

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.widget = prev.widget
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
        if isinstance(child, QtBaseLayout):
            self.widget = QtWidgets.QWidget()
            self.ui.setWidget(self.widget)
            self.widget.setLayout(child.outer)
            if not hasattr(self.widget, "origResizeEvent"):
                self.widget.origResizeEvent = self.widget.resizeEvent
            self.widget.resizeEvent = self.onUiResized
        elif isinstance(child, QtBaseWidget):
            self.ui.setWidget(child.outer)
            if not hasattr(child.outer, "origResizeEvent"):
                child.outer.origResizeEvent = child.outer.resizeEvent
            child.outer.resizeEvent = self.onUiResized
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
            self.widget.setParent(None)
        elif isinstance(child, QtBaseWidget):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])

    def onUiResized(self, event):
        node = self
        while node.retired_by:
            node = node.retired_by
        if node.widget:
            node.widget.resizeEvent = self.onUiResized
        else:
            node.children[0].outer.resizeEvent = self.onUiResized
        if node.widget:
            node.widget.origResizeEvent(event)
        elif node.children[0].outer:
            node.children[0].outer.origResizeEvent(event)
        else:
            node.children[0].children[0].outer.origResizeEvent(event)

        if node.horizontal is False:
            if isinstance(node.children[0], QtBaseLayout):
                node.outer.setMinimumWidth(node.children[0].outer.sizeHint().width())
            elif isinstance(node.children[0], QtBaseWidget):
                node.outer.setMinimumWidth(node.children[0].outer.sizeHint().width())

        if node.vertical is False:
            if isinstance(node.children[0], QtBaseLayout):
                node.outer.setMinimumHeight(node.children[0].outer.sizeHint().height())
            elif isinstance(node.children[0], QtBaseWidget):
                self.outer.setMinimumHeight(self.children[0].outer.sizeHint().height())
