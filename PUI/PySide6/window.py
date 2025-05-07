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
        self.node._keypress(e)

    def mousePressEvent(self, event):
        focused_widget = QtWidgets.QApplication.focusWidget()
        if isinstance(focused_widget, QtWidgets.QLineEdit):
            focused_widget.clearFocus()
        super().mousePressEvent(event)

class Window(QtBaseWidget):
    pui_terminal = False

    def __init__(self, title=None, icon=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        if icon:
            self.icon = QtGui.QIcon(icon)
        else:
            self.icon = None
        self.size = size
        self.maximize = maximize
        self.fullscreen = fullscreen

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.node = self
            self.curr_size = prev.curr_size
            self.curr_maximize = prev.curr_maximize
            self.curr_fullscreen = prev.curr_fullscreen
        else:
            self.ui = QMainWindow()
            self.ui.node = self
            self.ui.show()
            self.curr_size = Prop()
            self.curr_maximize = Prop()
            self.curr_fullscreen = Prop()

        if self.curr_size.set(self.size):
            self.ui.resize(*self.size)
        if self.curr_maximize.set(self.maximize):
            self.ui.resize(800, 600) # workaround on windows ref: https://stackoverflow.com/questions/27157312/qt-showmaximized-not-working-in-windows
            self.ui.showMaximized()
        if self.curr_fullscreen.set(self.fullscreen):
            self.ui.showFullScreen()
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
