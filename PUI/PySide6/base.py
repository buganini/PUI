from .. import *

from PySide6 import QtCore, QtWidgets

class QtViewSignal(QtCore.QObject):
    redraw = QtCore.Signal()

def _apply_params(ui, params):
    QtHorizontalPolicy = params.get("QtHorizontalPolicy")
    if not QtHorizontalPolicy is None:
        print("QtHorizontalPolicy")
        ui.sizePolicy().setHorizontalPolicy(QtHorizontalPolicy)

    QtVerticalPolicy = params.get("QtVerticalPolicy")
    if not QtVerticalPolicy is None:
        print("QtVerticalPolicy")
        ui.sizePolicy().setVerticalPolicy(QtVerticalPolicy)

    QtSizeConstraint = params.get("QtSizeConstraint")
    if not QtSizeConstraint is None:
        print("QtSizeConstraint")
        ui.setSizeConstraint(QtSizeConstraint)

class QPUIView(PUIView):
    def __init__(self):
        super().__init__()
        self.signal = QtViewSignal()
        self.signal.redraw.connect(self.update)

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self.layout_params)

    def redraw(self):
        self.signal.redraw.emit()

class QtBaseWidget(PUINode):
    terminal = True
    def destroy(self):
        self.ui.deleteLater()

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self.layout_params)

class QtBaseLayout(PUINode):
    def destroy(self):
        self.ui.deleteLater()

    def addChild(self, idx, child):
        from .layout import QtSpacerItem
        if isinstance(child, QtBaseLayout):
            self.ui.insertLayout(idx, child.ui)
        elif isinstance(child, QtSpacerItem):
            self.ui.insertItem(idx, child.ui)
        elif isinstance(child, QtBaseWidget):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.ui.insertWidget(idx, child.ui, **params)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        from .layout import QtSpacerItem
        if isinstance(child, QtBaseLayout):
            self.ui.removeItem(child.ui)
        elif isinstance(child, QtSpacerItem):
            self.ui.removeItem(child.ui)
        elif isinstance(child, QtBaseWidget):
            child.ui.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])
