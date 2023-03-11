from .. import *

class QtBaseWidget(PUINode):
    def destroy(self):
        pass
        # print("destroy")

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