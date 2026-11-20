from .. import *
from .base import *
from .layout import *

class Divider(QtBaseWidget):
    pui_movable = False

    def __init__(self):
        super().__init__()

    def _qt_static_policy(self, horizontal):
        # A line reports no minimum size, so Preferred lets a crowded box
        # shrink it to nothing; keep its thickness fixed.
        if horizontal == getattr(self.non_virtual_parent, 'container_x', False):
            return QtWidgets.QSizePolicy.Policy.Fixed
        return super()._qt_static_policy(horizontal)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QFrame()
        parent = self.non_virtual_parent
        vertical = getattr(parent, 'container_x', False)
        self.expand_x_prio = 0 if vertical else 1
        self.expand_y_prio = 1 if vertical else 0
        if getattr(parent, 'container_y', False):
            self.ui.setFrameShape(QtWidgets.QFrame.Shape.HLine)
        elif getattr(parent, 'container_x', False):
            self.ui.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        else:
            self.ui.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.ui.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        super().update(prev)
