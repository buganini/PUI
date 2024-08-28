from .. import *
from .base import *

class ComboBox(WxBaseWidget):
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
            self.ui = prev.ui
        else:
            self.curr_index = Prop()
            self.curr_text = Prop()
            self.ui = wx.ComboBox(getWindow(self.parent), choices=[])
            self.ui.Bind(wx.EVT_COMBOBOX, self._combobox)
            self.ui.Bind(wx.EVT_TEXT, self._text)

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

        if self.curr_index.set(index):
            self.ui.SetSelection(index)

        if self.curr_text.set(text):
            self.ui.SetValue(text)

    def _combobox(self, *args, **kwargs):
        node = self.get_node()
        idx = self.ui.GetSelection()
        if node.index_model:
            node.index_model.value = idx
        e = PUIEvent()
        e.value = idx
        node._change(e)

    def _text(self, *args, **kwargs):
        node = self.get_node()
        text = self.ui.GetValue()
        if node.text_model:
            node.text_model.value = text
        e = PUIEvent()
        e.value = text
        node._change(e)

    def addChild(self, idx, child):
        self.ui.Insert(child.text, idx)

    def removeChild(self, idx, child):
        self.ui.Delete(idx)


class ComboBoxItem(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text
