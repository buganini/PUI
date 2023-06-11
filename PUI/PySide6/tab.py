from .. import *
from .base import *

class QtTabWidget(QtBaseWidget):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    terminal = False
    def __init__(self, tabposision=NORTH):
        super().__init__()
        self.tabposision = tabposision

    def destroy(self, direct):
        if direct:
            for w in self.widgets:
                if w:
                    w.deleteLater()
        super().destroy(direct)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.widgets = prev.widgets
        else:
            self.ui = QtWidgets.QTabWidget()
            self.widgets = []
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, QtTab):
            raise RuntimeError("QtTabWidget can only contain QtTab")

        self._addChild(idx, child.children[0], child.label)

    def _addChild(self, idx, child, label):
        if isinstance(child, QtBaseLayout):
            widget = QtWidgets.QWidget()
            widget.setLayout(child.outer)
            self.ui.addTab(widget)
            self.widgets.append(widget)
        elif isinstance(child, QtBaseWidget):
            self.ui.addTab(child.outer, label)
            self.widgets.append(None)
        elif child.children:
            self._addChild(idx, child.children[0], label)

    def removeChild(self, idx, child):
        child.outer.setParent(None)
        frame = self.frame.pop(idx)
        if frame:
            frame.deleteLater()


class QtTab(PUINode):
    def __init__(self, label):
        super().__init__()
        self.label = label


    def addChild(self, idx, child):
        if idx > 0:
            raise RuntimeError("QtTab can only have one child")
