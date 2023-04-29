from .. import *

from PySide6 import QtCore, QtWidgets

class QtViewSignal(QtCore.QObject):
    redraw = QtCore.Signal()

class QPUIView(PUIView):
    def __init__(self):
        super().__init__()
        self.signal = QtViewSignal()
        self.signal.redraw.connect(self.update)

    def redraw(self):
        self.signal.redraw.emit()

class QtBaseWidget(PUINode):
    terminal = True
    def destroy(self):
        self.ui.deleteLater()

class QtBaseLayout(PUINode):
    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.ui.addLayout(child.ui)
        elif isinstance(child, QtBaseWidget):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.ui.addWidget(child.ui, **params)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.removeItem(child.ui)
        elif isinstance(child, QtBaseWidget):
            child.ui.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])
