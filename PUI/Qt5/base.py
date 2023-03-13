from .. import *
from PyQt5 import QtWidgets

class QtBaseWidget(PUINode):
    def destroy(self):
        self.ui.deleteLater()

class QtBaseLayout(PUINode):
    def addChild(self, child):
        if isinstance(child, QtBaseLayout):
            self.ui.addLayout(child.ui)
        else:
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.ui.addWidget(child.ui, **params)

    def removeChild(self, child):
        if isinstance(child, QtBaseLayout):
            self.ui.removeItem(child.ui)
        else:
            child.ui.setParent(None)