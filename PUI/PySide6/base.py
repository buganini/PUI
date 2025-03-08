from .. import *
from PySide6 import QtCore, QtWidgets, QtGui

class QtViewSignal(QtCore.QObject):
    redraw = QtCore.Signal()

def _apply_params(ui, node):
    styles = {}
    if node.style_fontsize:
        styles["font"] = f"{node.style_fontsize}pt"
    if node.style_fontfamily:
        styles["font-family"] = node.style_fontfamily
    if node.style_color:
        styles["color"] = f"#{node.style_color:06X}"
    if node.style_bgcolor:
        styles["background-color"] = f"#{node.style_bgcolor:06X}"

    style = node.qt_params.get("Style")
    if not style is None:
        ui.setStyle(style)

    HorizontalPolicy = node.qt_params.get("HorizontalPolicy")
    if not HorizontalPolicy is None:
        ui.sizePolicy().setHorizontalPolicy(HorizontalPolicy)

    VerticalPolicy = node.qt_params.get("VerticalPolicy")
    if not VerticalPolicy is None:
        ui.sizePolicy().setVerticalPolicy(VerticalPolicy)

    SizeConstraint = node.qt_params.get("SizeConstraint")
    if not SizeConstraint is None:
        ui.setSizeConstraint(SizeConstraint)

    StyleSheet = node.qt_params.get("StyleSheet", {})
    for k,v in StyleSheet.items():
        styles[k] = v

    if hasattr(ui, "setStyleSheet"):
        ui.setStyleSheet("".join([f"{k}:{v};" for k,v in styles.items()]))

    if node.layout_padding:
        ui.setContentsMargins(*trbl2ltrb(node.layout_padding))

class QtPUIView(PUIView):
    pui_virtual = True
    def __init__(self):
        super().__init__()
        self.qt_params = {}
        self._qtsignal = QtViewSignal()
        self._qtsignal.redraw.connect(self.sync, QtCore.Qt.ConnectionType.QueuedConnection) # Use QueuedConnection to prevent nested trigger

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
        self._qtsignal.redraw.emit()

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self)

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self

class QtBaseWidget(PUINode):
    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.qt_params = {}

    def destroy(self, direct):
        if direct:
            if self.ui:
                self.ui.deleteLater()
        self.ui = None
        super().destroy(direct)

    def update(self, prev=None):
        super().update(prev)

        sizePolicy = self.ui.sizePolicy()
        if self.layout_width is not None:
            sizePolicy.setHorizontalPolicy(QtWidgets.QSizePolicy.Preferred)
        if self.layout_height is not None:
            sizePolicy.setVerticalPolicy(QtWidgets.QSizePolicy.Preferred)
        self.ui.setSizePolicy(sizePolicy)

        if not hasattr(self.ui, "origSizeHint"):
            self.ui.origSizeHint = self.ui.sizeHint
        self.ui.sizeHint = self.qtSizeHint

        _apply_params(self.ui, self)

    def qtSizeHint(self):
        node = self.get_node()
        if not node.ui:
            return QtCore.QSize(0, 0)
        sh = node.ui.origSizeHint()
        w = sh.width()
        h = sh.height()
        if not node.layout_width is None:
            w = node.layout_width
        if not node.layout_height is None:
            h = node.layout_height
        return QtCore.QSize(w, h)

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self

class QtBaseLayout(PUINode):
    def __init__(self):
        super().__init__()
        self.qt_params = {}
        if not isinstance(self.non_virtual_parent, QtBaseLayout):
            self.layout_padding = (11,11,11,11)

    @property
    def outer(self):
        return self.ui

    @property
    def inner(self):
        return self.layout

    def destroy(self, direct):
        if direct:
            if self.ui:
                self.ui.deleteLater()
        self.layout = None
        self.ui = None
        super().destroy(direct)

    def update(self, prev=None):
        super().update(prev)
        _apply_params(self.ui, self)

    def addChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.layout.insertItem(idx, child.outer)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.layout.insertWidget(idx, child.outer, **params)

    def removeChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.layout.removeItem(child.outer)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)

    def qt(self, **kwargs):
        for k,v in kwargs.items():
            self.qt_params[k] = v
        return self

class QtBaseFrame(QtBaseWidget):
    pui_terminal = False

    def destroy(self, direct):
        if direct:
            if self.ui:
                self.ui.deleteLater()
                self.ui = None

    def addChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.setWidget(child.outer)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        elif child.children:
            self.removeChild(idx, child.children[0])

class QtInPui(QtBaseWidget):
    def __init__(self, widget, *args):
        self._internal_tag = str(id(widget))
        super().__init__(*args)
        self.ui = widget

    def destroy(self, direct):
        pass

class PuiInQt(QtPUIView):
    def __init__(self, ui):
        super().__init__()
        self.ui = ui
        self.ui.update()

    def addChild(self, idx, child):
        self.ui.addChild(idx, child)

    def removeChild(self, idx, child):
        self.ui.removeChild(idx, child)