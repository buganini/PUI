from .. import *
from .base import *

class ProgressBar(QtBaseWidget):
    def __init__(self, progress, maximum=1):
        super().__init__()
        self.progress = progress*100
        self.maximum = maximum*100

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = QtWidgets.QProgressBar()
        self.ui.setMaximum(self.maximum)
        self.ui.setValue(int(self.progress))
        super().update(prev)
