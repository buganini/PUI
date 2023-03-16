from .. import *
from PyQt5 import QtCore, QtWidgets

class QtBaseWidget(PUINode):
    def destroy(self):
        self.ui.deleteLater()

class QtBaseLayout(PUINode):
    def addChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.ui.addLayout(child.ui)
        elif isinstance(child, QtBaseWidget):
            params = {}
            if not child.layout_weight is None:
                params["stretch"] = child.layout_weight
            self.ui.addWidget(child.ui, **params)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, QtBaseLayout):
            self.box.removeItem(child.ui)
        elif isinstance(child, QtBaseWidget):
            child.ui.setParent(None)
        else:
            self.removeChild(idx, child.children[0])
