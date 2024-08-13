from .. import *
from .base import *

class ToolBar(PUINode):
    pui_outoforder = True
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.actions = prev.actions
        else:
            self.ui = QtWidgets.QToolBar()
            self.actions = []

        super().update(prev)

    def addChild(self, idx, child):
        if idx < len(self.actions):
            if isinstance(child, ToolBarAction):
                self.actions.insert(idx, self.ui.insertAction(self.actions[idx], child.outer))
            else:
                self.actions.insert(idx, self.ui.insertWidget(self.actions[idx], child.outer))
        else:
            if isinstance(child, ToolBarAction):
                self.actions.append(self.ui.addAction(child.outer))
            else:
                self.actions.append(self.ui.addWidget(child.outer))

    def removeChild(self, idx, child):
        self.ui.removeAction(self.actions[idx])

class ToolBarAction(PUINode):
    def __init__(self, text, icon=None):
        super().__init__()
        self.text = text
        self.icon = icon
        self.onTriggered = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.triggered.disconnect()
        else:
            self.ui = QtGui.QAction(self.text)
        if self.icon:
            self.ui.setIcon(self.icon)
        self.ui.triggered.connect(self._triggered)

        super().update(prev)

    def _triggered(self):
        node = self.get_node()
        if node.onTriggered:
            node.onTriggered[0](*node.onTriggered[1], **node.onTriggered[2])

    def trigger(self, callback, *cb_args, **cb_kwargs):
        self.onTriggered = (callback, cb_args, cb_kwargs)
