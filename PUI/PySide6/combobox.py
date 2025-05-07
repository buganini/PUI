from .. import *
from .base import *

class ComboBox(QtBaseWidget):
    pui_terminal = False
    def __init__(self, editable=False, index_model=None, text_model=None):
        super().__init__()
        self.editable = editable
        self.index_model = index_model
        self.text_model = text_model

    def update(self, prev):
        if prev and prev.ui:
            self.curr_index = prev.curr_index
            self.curr_text = prev.curr_text
            self.signal_connected = prev.signal_connected
            self.ui = prev.ui
        else:
            self.curr_index = Prop()
            self.curr_text = Prop()
            self.signal_connected = False
            self.ui = QtWidgets.QComboBox()
        self.ui.setEditable(self.editable)
        super().update(prev)

    def postSync(self):
        index = -1
        text = ""

        if self.index_model:
            index = self.index_model.value
            text = self.children[index].text
        elif self.text_model:
            text = str(self.text_model.value)
            try:
                index = [c.value for c in self.children].index(text)
            except:
                index = -1

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
        if self.text_model:
            self.text_model.value = self.children[idx].value
        e = PUIEvent()
        e.value = idx
        self._change(e)

    def on_currentTextChanged(self, text):
        if not self.editable:
            return
        if self.text_model:
            self.text_model.value = text
        e = PUIEvent()
        e.value = text
        self._change(e)

    def addChild(self, idx, child):
        self.ui.insertItem(idx, child.text)

    def removeChild(self, idx, child):
        self.ui.removeItem(idx)

class ComboBoxItem(PUINode):
    def __init__(self, text, value=None):
        super().__init__()
        self.id(text)
        self.text = text
        if value is None:
            value = text
        self.value = value
