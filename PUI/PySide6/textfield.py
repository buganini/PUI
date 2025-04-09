from .. import *
from .base import *

class TextField(QtBaseWidget):
    def __init__(self, model, edit_model=None):
        super().__init__()
        self.model = model
        self.edit_model = edit_model
        self.editing = False

    def update(self, prev):
        model_value = str(self.model.value)
        if prev and prev.ui:
            self.editing = prev.editing
            self.ui = prev.ui
            self.curr_value = prev.curr_value
            self.ui.node = self
            self.ui.textChanged.disconnect()
            if self.curr_value.set(model_value) and not self.editing:
                self.ui.setText(model_value)
            self.ui.textChanged.connect(self.on_textchanged)
            self.ui.editingFinished.disconnect()
            self.ui.editingFinished.connect(self.on_editing_finished)
        else:
            self.ui = QtWidgets.QLineEdit()
            self.ui.setFocusPolicy(QtCore.Qt.ClickFocus | QtCore.Qt.NoFocus)
            self.ui.node = self
            self.ui.setText(model_value)
            self.curr_value = Prop(model_value)
            self.ui.textChanged.connect(self.on_textchanged)
            self.ui.editingFinished.connect(self.on_editing_finished)

        if self.edit_model and not self.editing:
            self.edit_model.value = model_value

        super().update(prev)

    def on_editing_finished(self):
        node = self.get_node()
        node.editing = False
        value = self.ui.text()
        node.model.value = value
        if node.edit_model:
            node.edit_model.value = value
        model_value = str(self.model.value)
        self.ui.blockSignals(True)
        self.ui.setText(model_value)
        self.ui.blockSignals(False)
        e = PUIEvent()
        e.value = value
        self._change(e)
        node.ui.clearFocus()

    def on_textchanged(self):
        node = self.get_node()
        value = self.ui.text()
        if node.edit_model:
            node.editing = True
            node.edit_model.value = value
        else:
            node.model.value = value
        e = PUIEvent()
        e.value = value
        self._input(e)
