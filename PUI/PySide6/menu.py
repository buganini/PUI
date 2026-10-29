from .. import *
from .base import *
from .layout import Spacer

class MenuBar(PUINode):
    pui_outoforder = True

    def __init__(self, *, native=True):
        super().__init__()
        self.native = native
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.actions = prev.actions
        else:
            self.ui = QtWidgets.QMenuBar()
            self.actions = []

        self.ui.setNativeMenuBar(self.native)
        super().update(prev)

    def addChild(self, idx, child):
        # Keep a logical slot for ignored spacers so subsequent indices agree
        # with the declarative tree, including keyed moves and removals.
        if isinstance(child, Spacer):
            self.actions.insert(idx, None)
            return
        if not isinstance(child, (Menu, MenuAction)):
            raise TypeError('MenuBar children must be Menu, MenuAction or Spacer')
        action = child.ui.menuAction() if isinstance(child, Menu) else child.ui
        before = next((a for a in self.actions[idx:] if a is not None), None)
        if before is None:
            self.ui.addAction(action)
        else:
            self.ui.insertAction(before, action)
        self.actions.insert(idx, action)

    def removeChild(self, idx, child):
        action = self.actions.pop(idx)
        if action is not None:
            self.ui.removeAction(action)

class Menu(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setTitle(self.text)
            self.actions = prev.actions
        else:
            self.ui = QtWidgets.QMenu(self.text)
            self.actions = []

        super().update(prev)

    def addChild(self, idx, child):
        if idx < len(self.actions):
            if isinstance(child, Menu):
                self.actions.insert(idx, self.ui.insertMenu(self.actions[idx], child.outer))
            elif isinstance(child, MenuAction):
                self.actions.insert(idx, self.ui.insertAction(self.actions[idx], child.outer))
        else:
            if isinstance(child, Menu):
                self.actions.append(self.ui.addMenu(child.outer))
            elif isinstance(child, MenuAction):
                self.actions.append(self.ui.addAction(child.outer))

    def removeChild(self, idx, child):
        self.ui.removeAction(self.actions[idx])

class MenuAction(PUINode):
    def __init__(self, text, *, native=True):
        super().__init__()
        self.text = text
        self.native = native
        self.qt_role = None
        self.onTriggered = None

    def qt(self, *, role=None, **kwargs):
        """Override native role inference with a QAction.MenuRole enum."""
        if role is not None:
            if not isinstance(role, QtGui.QAction.MenuRole):
                raise TypeError('role must be a QAction.MenuRole')
            self.qt_role = role
        return super().qt(**kwargs)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.setText(self.text)
            self.ui.triggered.disconnect()
        else:
            self.ui = QtGui.QAction(self.text)
        role = self.qt_role
        if role is None:
            role = (QtGui.QAction.MenuRole.TextHeuristicRole if self.native
                    else QtGui.QAction.MenuRole.NoRole)
        self.ui.setMenuRole(role)
        self.ui.triggered.connect(self._triggered)

        super().update(prev)

    def _triggered(self):
        node = self.get_node()
        if node.onTriggered:
            node.onTriggered[0](*node.onTriggered[1], **node.onTriggered[2])

    def trigger(self, callback, *cb_args, **cb_kwargs):
        self.onTriggered = (callback, cb_args, cb_kwargs)
