from __future__ import annotations
from .. import _typing as _t
from ..refs import NodeBinder as _NodeBinder
from .. import *
from .base import *
from .menu import *
from .modal import *
from .toolbar import *
from PySide6 import QtWidgets

class QMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        # A top-level window is the boundary of the layout.  Without this,
        # QMainWindowLayout propagates a growing central widget's minimum size
        # to the native window.  The window can then become larger than the
        # screen and Qt does not shrink it again when the content gets smaller.
        self.layout().setSizeConstraint(
            QtWidgets.QLayout.SizeConstraint.SetNoConstraint
        )

    def keyPressEvent(self, event):
        e = PUIEvent()
        e.text = event.text()
        self.puinode._keypress(e)

    def mousePressEvent(self, event):
        focused_widget = QtWidgets.QApplication.focusWidget()
        if isinstance(focused_widget, QtWidgets.QLineEdit):
            focused_widget.clearFocus()
        super().mousePressEvent(event)

class _WindowBinder(_NodeBinder):
    def _set_flag(self, flag, enabled):
        def apply(node, value):
            ui = node.ui
            flags = ui.windowState()
            ui.setWindowState(flags | flag if value else flags & ~flag)
            ui.show()
        self._schedule(enabled, apply)

    def maximize(self, enabled: bool):
        self._set_flag(QtCore.Qt.WindowState.WindowMaximized, enabled)

    def minimize(self, enabled: bool):
        self._set_flag(QtCore.Qt.WindowState.WindowMinimized, enabled)

    def fullscreen(self, enabled: bool):
        self._set_flag(QtCore.Qt.WindowState.WindowFullScreen, enabled)


class Window(QtWindowState, QtBaseWidget):
    def __pui_binder__(self):
        return _WindowBinder(self, self.get_poster())

    pui_terminal = False

    def __init__(
        self,
        title: str | None = None,
        icon: _t.Any = None,
        size: tuple[int, int] | None = None,
        maximize: bool | None = None,
        fullscreen: bool | None = None,
    ) -> None:
        super().__init__()
        self.title = title
        if icon:
            self.icon = QtGui.QIcon(icon)
        else:
            self.icon = None
        self.size = size
        self._initial_maximize = maximize
        self._initial_fullscreen = fullscreen

    def update(self, prev=None):
        creating = not (prev and prev.ui)
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.puinode = self
            self.curr_size = prev.curr_size
        else:
            self.ui = QMainWindow()
            self.ui.puinode = self
            self.ui.show()
            self.curr_size = Prop()

        if self.curr_size.set(self.size) and self.size is not None:
            self.ui.resize(*self.size)
        if creating:
            self._apply_initial_window_state()
        title = window_title(self)
        if title is not None:
            self.ui.setWindowTitle(title)
        if not self.icon is None:
            self.ui.setWindowIcon(self.icon)
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, MenuBar):
            self.ui.setMenuBar(child.outer)
        elif isinstance(child, ToolBar):
            self.ui.addToolBar(child.outer)
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            self.ui.setCentralWidget(child.outer)
        else:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        if isinstance(child, MenuBar):
            child.outer.close()
        elif isinstance(child, Modal):
            pass
        elif isinstance(child, QtBaseWidget) or isinstance(child, QtBaseLayout):
            child.outer.setParent(None)
        else:
            self.removeChild(idx, child.children[0])
