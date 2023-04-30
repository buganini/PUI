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
            self.ui.setWidget(self.widget)

    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.widget.setLayout(child.ui)
        elif isinstance(child, QtBaseWidget):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.widget.setWidget(child.ui, **params)

    def removeChild(self, idx, child):
        child.ui.setParent(None)
