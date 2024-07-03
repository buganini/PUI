from .. import *
from .base import *

class ComboBox(QtBaseWidget):
    terminal = False
    def __init__(self, editable=False, index_model=None, text_model=None):
        super().__init__()
        self.editable = editable
        self.index_model = index_model
        self.text_model = text_model
        self.index_changed = None
        self.text_changed = None

    def on(self, index_changed=None, text_changed=None):
        if index_changed:
            self.index_changed = index_changed
        if text_changed:
            self.text_changed = text_changed
        return self

    def update(self, prev):
        if prev and prev.ui:
            self.curr_index = prev.curr_index
            self.curr_text = prev.curr_text
            self.signal_connected = prev.signal_connected
            self.ui = prev.ui
        else:
            self.curr_index = Prop(None)
            self.curr_text = Prop(None)
            self.signal_connected = False
            self.ui = QtWidgets.QComboBox()
        self.ui.setEditable(self.editable)
        super().update(prev)

    def postSync(self):
        if self.index_model:
            index = self.index_model.value
            text = self.children[index].text
        elif self.text_model:
            text = str(self.text_model.value)
            try:
                index = [c.text for c in self.children].index(text)
            except:
                index = 0

        if self.signal_connected:
            self.ui.currentIndexChanged.disconnect()
            self.ui.currentTextChanged.disconnect()

        if self.curr_index.set(index):
            self.ui.setCurrentIndex(index)

        if self.curr_text.set(text):
            self.ui.setCurrentText(text)

        self.ui.currentIndexChanged.connect(self.on_currentIndexChanged)
        self.ui.currentTextChanged.connect(self.on_currentTextChanged)


    def on_currentIndexChanged(self, idx):
        if self.index_model:
            self.index_model.value = idx
        if self.index_changed:
            self.index_changed(idx)

    def on_currentTextChanged(self, text):
        if self.text_model:
            self.text_model.value = text
        if self.text_changed:
            self.text_changed(text)

    def addChild(self, idx, child):
        self.ui.insertItem(idx, child.text)

    def removeChild(self, idx, child):
        self.ui.removeItem(idx)

class ComboBoxItem(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text
