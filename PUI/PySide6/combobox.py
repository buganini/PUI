from .. import *
from .base import *

class QtComboBox(QtBaseWidget):
    terminal = False
    def __init__(self, editable=False, index_model=None, text_model=None):
        super().__init__()
        self.editable = editable
        if index_model is None:
            index_model = DummyBinding(0)
        if text_model is None:
            text_model = DummyBinding("")
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
        index = self.index_model.value
        text = self.text_model.value
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            if prev.last_index != index:
                self.ui.currentIndexChanged.disconnect()
                self.ui.setCurrentIndex(index)
                self.ui.currentIndexChanged.connect(self.on_currentIndexChanged)
            self.last_index = index

            if prev.last_text != text:
                self.ui.currentTextChanged.disconnect()
                self.ui.setCurrentText(text)
                self.ui.currentTextChanged.connect(self.on_currentTextChanged)
            self.last_text = text
        else:
            self.last_index = index
            self.last_text = text
            self.ui = QtWidgets.QComboBox()
            self.ui.currentIndexChanged.connect(self.on_currentIndexChanged)
            self.ui.currentTextChanged.connect(self.on_currentTextChanged)
        self.ui.setEditable(self.editable)
        super().update(prev)

    def on_currentIndexChanged(self, idx):
        self.index_model.value = idx
        if self.index_changed:
            self.index_changed(idx)

    def on_currentTextChanged(self, text):
        self.text_model.value = text
        if self.text_changed:
            self.text_changed(text)

    def addChild(self, idx, child):
        self.ui.insertItem(idx, child.text)

    def removeChild(self, idx, child):
        self.ui.removeItem(idx)

class QtComboBoxItem(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text
