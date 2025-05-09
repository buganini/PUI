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

class EventFilter(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.node = None

    def eventFilter(self, obj, event):
        node = self.node.get_node()
        if event.type() == QtCore.QEvent.DragEnter:
            return node.handleDragEnterEvent(event)
        elif event.type() == QtCore.QEvent.Drop:
            return node.handleDropEvent(event)
        return super().eventFilter(obj, event)

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

        if prev:
            self.eventFilter = prev.eventFilter
        else:
            self.eventFilter = EventFilter()
        self.eventFilter.node = self

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

    def postUpdate(self):
        if self.ui:
            if self._onDropped:
                self.ui.setAcceptDrops(True)
                self.ui.installEventFilter(self.eventFilter)
            else:
                self.ui.setAcceptDrops(False)
        super().postUpdate()

    def handleDragEnterEvent(self, event):
        if self._onDragEntered:
            self._onDragEntered[0](event, *self._onDragEntered[1], **self._onDragEntered[2])
        else:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()

    def handleDropEvent(self, event):
        if self._onDropped:
            self._onDropped[0](event, *self._onDropped[1], **self._onDropped[2])
        else:
            print("Dropped", event)
            event.ignore()

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
        if prev and prev.ui:
            self.mounted_children = prev.mounted_children
        else:
            self.mounted_children = []

        super().update(prev)
        _apply_params(self.ui, self)

    def addChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.qtlayout.insertItem(idx, child.outer)
            self.mounted_children.insert(idx, child)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.qtlayout.insertWidget(idx, child.outer, **params)
            self.mounted_children.insert(idx, child)

    def removeChild(self, idx, child):
        from .modal import Modal
        from .layout import Spacer
        if isinstance(child, Spacer):
            self.qtlayout.removeItem(child.outer)
            self.mounted_children.pop(idx)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
            self.mounted_children.pop(idx)

    def postUpdate(self):
        super().postUpdate()

        for i, child in enumerate(self.mounted_children):
            child = child.get_node()
            self.mounted_children[i] = child.get_node()

            weight = child.layout_weight
            self.qtlayout.setStretch(i, weight if weight else 0)

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