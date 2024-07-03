from .. import *
from .base import *

class TextField(QtBaseWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.editing = False
        self.changed_cb = None

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.ui.focusOutEvent = self.focusOutEvent
            self.curr_value = prev.curr_value
            if self.curr_value.set(model_value):
                self.ui.textChanged.disconnect()
                if not self.editing or not model_value:
                    self.ui.setText(model_value)
                self.ui.textChanged.connect(self.on_textchanged)
        else:
            self.ui = QtWidgets.QLineEdit()
            self.ui.origFocusOutEvent = self.ui.focusOutEvent
            self.ui.focusOutEvent = self.focusOutEvent
            self.ui.setText(model_value)
            self.curr_value = Prop(model_value)
            self.ui.textChanged.connect(self.on_textchanged)
        super().update(prev)

    def change(self, cb, *args, **kwargs):
        self.changed_cb = (cb, args, kwargs)

    def on_textchanged(self):
        node = self.get_node()
        node.editing = True
        node.model.value = self.ui.text()
        if node.changed_cb:
            node.changed_cb[0](*node.changed_cb[1], **node.changed_cb[2])

    def focusOutEvent(self, event):
        node = self.get_node()
        node.editing = False
        node.ui.origFocusOutEvent(event)
