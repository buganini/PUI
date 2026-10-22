from .base import *
from .layout import VBox
from ..views import ViewsMixin


class Views(ViewsMixin, QtBaseWidget):
    expand_x_prio = expand_y_prio = 3
    def _page(self):
        return VBox().layout(padding=0)

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QStackedWidget()
            self.ui.addWidget(QtWidgets.QWidget())  # Native empty selection.
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.insertWidget(idx + 1, child.outer)

    def removeChild(self, idx, child):
        self.ui.removeWidget(child.outer)
        child.outer.setParent(None)

    def _show_view(self, index):
        self.ui.setCurrentIndex(0 if index is None else index + 1)
