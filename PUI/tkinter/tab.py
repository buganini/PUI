from .. import *
from .base import *

class TkNotebook(TkBaseWidget):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    terminal = False
    def __init__(self, tabposition=NORTH):
        super().__init__()
        self.tabposition = tabposition

    def destroy(self, direct):
        if direct:
            for w in self.widgets:
                if w:
                    w.deleteLater()
        super().destroy(direct)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ttk.Notebook(self.tkparent.inner)
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, TkNotebookFrame):
            raise RuntimeError("TkNotebook can only contain TkNotebookFrame")

        self._addChild(idx, child.children[0], child.label)

    def _addChild(self, idx, child, label):
        if isinstance(child, TkBaseWidget):
            self.ui.add(child.outer, text=label)
        elif child.children:
            self._addChild(idx, child.children[0], label)

    def removeChild(self, idx, child):
        if isinstance(child, TkBaseWidget):
            self.ui.forget(child.outer)
        elif child.children:
            self.removeChild(idx, child.children[0])

class TkNotebookFrame(PUINode):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def addChild(self, idx, child):
        if idx > 0:
            raise RuntimeError("TkNotebookFrame can only have one child")
