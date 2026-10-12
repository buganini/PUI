from .. import *
from .base import *
from .menu import *
from .modal import *
from .toolbar import *
from PySide6 import QtWidgets

class QMainWindow(QtWidgets.QMainWindow):
    def keyPressEvent(self, event):
        e = PUIEvent()
        e.text = event.text()
        self.puinode._keypress(e)

    def mousePressEvent(self, event):
        focused_widget = QtWidgets.QApplication.focusWidget()
        if isinstance(focused_widget, QtWidgets.QLineEdit):
            focused_widget.clearFocus()
        super().mousePressEvent(event)

class Window(QtWindowState, QtBaseWidget):
    pui_terminal = False

    def __init__(self, title=None, icon=None, size=None, maximize=None, fullscreen=None):
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
            if self._initial_maximize is not None:
                self.maximize(self._initial_maximize)
            if self._initial_fullscreen is not None:
                self.fullscreen(self._initial_fullscreen)
        if not self.title is None:
            self.ui.setWindowTitle(self.title)
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
