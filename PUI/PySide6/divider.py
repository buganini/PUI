from .. import *
from .base import *
from .layout import *

class Divider(QtBaseWidget):
    pui_movable = False

    def __init__(self):
        super().__init__()

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QFrame()
            parent = self.non_virtual_parent
            if isinstance(parent, VBox):
                self.ui.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            elif isinstance(parent, HBox):
                self.ui.setFrameShape(QtWidgets.QFrame.Shape.VLine)
            else:
                self.ui.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
            self.ui.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)

        super().update(prev)
