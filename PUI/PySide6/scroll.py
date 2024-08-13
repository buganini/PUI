from .. import *
from .base import *
from PySide6.QtWidgets import QSizePolicy
import math

class Scroll(QtBaseWidget):
    pui_terminal = False
    END = -0.0

    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        self.align_x = 0
        self.align_y = 0
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.align_x = prev.align_x
            self.align_y = prev.align_y
            if prev.vsb_conn:
                vsb = self.ui.verticalScrollBar()
                vsb.valueChanged.disconnect(prev.vsb_conn)
                vsb.rangeChanged.disconnect(prev.vsb_range_conn)
            if prev.hsb_conn:
                hsb = self.ui.horizontalScrollBar()
                hsb.valueChanged.disconnect(prev.hsb_conn)
                hsb.rangeChanged.disconnect(prev.hsb_range_conn)
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
        vsb = self.ui.verticalScrollBar()
        self.vsb_conn = vsb.valueChanged.connect(self.vsb_changed)
        self.vsb_range_conn = vsb.rangeChanged.connect(self.vsb_range_changed)
        hsb = self.ui.horizontalScrollBar()
        self.hsb_conn = hsb.valueChanged.connect(self.hsb_changed)
        self.hsb_range_conn = hsb.rangeChanged.connect(self.hsb_range_changed)
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            return
        if isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.setWidget(child.outer)
            if not hasattr(child.outer, "origResizeEvent"):
                child.outer.origResizeEvent = child.outer.resizeEvent
                child.outer.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred))
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
                node.outer.setMinimumHeight(node.children[0].outer.sizeHint().height())

    def scrollX(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_x = 0
            self.hsb_offset = pos
        else:
            self.align_x = 1
            self.hsb_offset = abs(pos)
        return self

    def scrollY(self, pos=0):
        if math.copysign(1, pos) >= 0:
            self.align_y = 0
            self.vsb_offset = pos
        else:
            self.align_y = 1
            self.vsb_offset = abs(pos)
        return self

    def hsb_changed(self, *args, **kwargs):
        hsb = self.ui.horizontalScrollBar()
        v = hsb.value()
        if v < 10 and v > hsb.maximum() - 10:
            pass
        elif v < 10:
            self.align_x = 0
        elif v > hsb.maximum() - 10:
            self.align_x = 1

    def vsb_changed(self, *args, **kwargs):
        vsb = self.ui.verticalScrollBar()
        v = vsb.value()
        if v < 10 and v > vsb.maximum() - 10:
            pass
        elif v < 10:
            self.align_y = 0
        elif v > vsb.maximum() - 10:
            self.align_y = 1

    def preSync(self):
        hsb = self.ui.horizontalScrollBar()
        if self.align_x == 0:
            self.hsb_offset = hsb.value()
        else:
            self.hsb_offset = hsb.maximum() - hsb.value()
        vsb = self.ui.verticalScrollBar()
        if self.align_y == 0:
            self.vsb_offset = vsb.value()
        else:
            self.vsb_offset = vsb.maximum() - vsb.value()

    def vsb_range_changed(self, min, max):
        vsb = self.ui.verticalScrollBar()
        if self.align_y == 0:
            vsb.setValue(self.vsb_offset)
        else:
            vsb.setValue(max - self.vsb_offset)

    def hsb_range_changed(self, min, max):
        hsb = self.ui.verticalScrollBar()
        if self.align_y == 0:
            hsb.setValue(self.hsb_offset)
        else:
            hsb.setValue(max - self.hsb_offset)
