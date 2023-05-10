from .. import *

from PySide6 import QtCore, QtWidgets

class QtViewSignal(QtCore.QObject):
    redraw = QtCore.Signal()

def _apply_params(ui, params):
    HorizontalPolicy = params.get("HorizontalPolicy")
    if not HorizontalPolicy is None:
        ui.sizePolicy().setHorizontalPolicy(HorizontalPolicy)

    VerticalPolicy = params.get("VerticalPolicy")
    if not VerticalPolicy is None:
        ui.sizePolicy().setVerticalPolicy(VerticalPolicy)

    SizeConstraint = params.get("SizeConstraint")
    if not SizeConstraint is None:
        ui.setSizeConstraint(SizeConstraint)

    StyleSheet = params.get("StyleSheet")
    if not StyleSheet is None:
        ui.setStyleSheet(StyleSheet)

class QPUIView(PUIView):
    def __init__(self):
        super().__init__()
        self.qt_params = {}
        self.signal = QtViewSignal()
        self.signal.redraw.connect(self.update)

    def destroy(self, direct):
        if direct:
            if self.ui: # PUIView doesn't have ui
                self.ui.deleteLater()
        self.ui = None
        super().destroy(direct)

    def redraw(self):
        self.dirty = True
        if self.updating:
            return
        self.updating = True
        self.signal.redraw.emit()

    def update(self, prev=None):
        if self.retired_by:
            return
        self.dirty = False
        super().update(prev)
        _apply_params(self.ui, self.qt_params)
        self.updating = False
        if self.dirty:
            self.update(prev)

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self

class QtBaseWidget(PUINode):
    terminal = True

    def __init__(self):
        super().__init__()
        self.qt_params = {}

    def destroy(self, direct):
        if direct:
            self.ui.deleteLater()
        self.ui = None
        super().destroy(direct)

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self.qt_params)

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self

class QtBaseLayout(PUINode):
    def __init__(self):
        super().__init__()
        self.qt_params = {}

    def destroy(self, direct):
        if direct:
            self.ui.deleteLater()
        self.ui = None
        super().destroy(direct)

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self.qt_params)

    def addChild(self, idx, child):
        from .layout import QtSpacerItem
        if isinstance(child, QtBaseLayout):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.ui.insertLayout(idx, child.ui, **params)
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

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self