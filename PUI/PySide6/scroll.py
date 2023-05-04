from .. import *
from .base import *

class QtScrollArea(QtBaseWidget):
    terminal = False

    def destroy(self):
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
            self.widget = QtWidgets.QWidget()
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.ui.setWidget(self.widget)
            self.widget.setLayout(child.ui)
        elif isinstance(child, QtBaseWidget):
            self.ui.setWidget(child.ui)

    def removeChild(self, idx, child):
        child.ui.setParent(None)
