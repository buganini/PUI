from .. import *
from .base import *

class QtMenuBar(PUINode):
    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.actions = prev.actions
        else:
            self.ui = QtWidgets.QMenuBar()
            self.actions = []

        super().update(prev)

    def addChild(self, idx, child):
        if idx < len(self.actions):
            if isinstance(child, QtMenu):
                self.actions.insert(idx, self.ui.insertMenu(self.actions[idx], child.outer))
            elif isinstance(child, QtAction):
                self.actions.insert(idx, self.ui.insertAction(self.actions[idx], child.outer))
        else:
            if isinstance(child, QtMenu):
                self.actions.append(self.ui.addMenu(child.outer))
            elif isinstance(child, QtAction):
                self.actions.append(self.ui.addAction(child.outer))

    def removeChild(self, idx, child):
        self.ui.removeAction(self.actions[idx])

class QtMenu(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setTitle(self.text)
            self.actions = prev.actions
        else:
            self.ui = QtWidgets.QMenu(self.text)
            self.actions = []

        super().update(prev)

    def addChild(self, idx, child):
        if idx < len(self.actions):
            if isinstance(child, QtMenu):
                self.actions.insert(idx, self.ui.insertMenu(self.actions[idx], child.outer))
            elif isinstance(child, QtAction):
                self.actions.insert(idx, self.ui.insertAction(self.actions[idx], child.outer))
        else:
            if isinstance(child, QtMenu):
                self.actions.append(self.ui.addMenu(child.outer))
            elif isinstance(child, QtAction):
                self.actions.append(self.ui.addAction(child.outer))

    def removeChild(self, idx, child):
        self.ui.removeAction(self.actions[idx])

class QtAction(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text
        self.onTriggered = None

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.triggered.disconnect()
        else:
            self.ui = QtGui.QAction(self.text)
        self.ui.triggered.connect(self._triggered)

        super().update(prev)

    def _triggered(self):
        node = self.get_node()
        if node.onTriggered:
            node.onTriggered[0](*node.onTriggered[1], **node.onTriggered[2])

    def trigger(self, callback, *cb_args, **cb_kwargs):
        self.onTriggered = (callback, cb_args, cb_kwargs)
