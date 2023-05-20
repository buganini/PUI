from .. import *
from .base import *

class QtLineEdit(QtBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.editing = False

    def update(self, prev):
        value = self.model.value
        if prev and hasattr(prev, "ui"):
            self.editing = prev.editing
            self.ui = prev.ui
            self.ui.focusOutEvent = self.focusOutEvent
            if prev.last_value != value:
                self.ui.textChanged.disconnect()
                if not self.editing:
                    self.ui.setText(str(value))
                self.ui.textChanged.connect(self.on_textchanged)
            self.last_value = value
        else:
            self.last_value = value
            self.ui = QtWidgets.QLineEdit()
            self.ui.origFocusOutEvent = self.ui.focusOutEvent
            self.ui.focusOutEvent = self.focusOutEvent
            self.ui.setText(str(value))
            self.ui.textChanged.connect(self.on_textchanged)
        super().update(prev)

    def on_textchanged(self):
        node = self.get_node()
        node.editing = True
        node.model.value = self.ui.text()

    def focusOutEvent(self, event):
        node = self.get_node()
        node.editing = False
        node.ui.origFocusOutEvent(event)
