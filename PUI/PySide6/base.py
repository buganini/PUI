from .. import *

from PySide6 import QtWidgets

class QtBaseWidget(PUINode):
    def destroy(self):
        self.ui.deleteLater()

class QtBaseLayout(PUINode):
    def addChild(self, child):
        if isinstance(child, QtBaseLayout):
            self.ui.addLayout(child.ui)
        else:
            self.ui.addWidget(child.ui)

    def removeChild(self, child):
        if isinstance(child, QtBaseLayout):
            self.ui.removeItem(child.ui)
        else:
            child.ui.setParent(None)