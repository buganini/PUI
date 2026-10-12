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
            self.ui.Unbind(wx.EVT_COMBOBOX)
            self.ui.Unbind(wx.EVT_TEXT)
        else:
            self.curr_index = Prop()
            self.curr_text = Prop()
            self.ui = wx.ComboBox(getWindow(self.parent), choices=[], style=0 if self.editable else wx.CB_READONLY)
        self.ui.Bind(wx.EVT_COMBOBOX, self._combobox)
        self.ui.Bind(wx.EVT_TEXT, self._text)

        super().update(prev)

    def postSync(self):
        # Native choices must follow updated labels as well as insertions/removals.
        value = self.ui.GetValue()
        if self.ui.GetItems() != [c.text for c in self.children]:
            self.ui.SetItems([c.text for c in self.children])
        self.ui.SetEditable(self.editable)
        index = -1
        text = value if self.editable else ""
        if self.index_model is not None:
            requested = self.index_model.value
            if isinstance(requested, int) and 0 <= requested < len(self.children):
                index = requested
                text = self.children[index].text
            else:
                text = ""
        elif self.text_model is not None:
            text = str(self.text_model.value)
            index = next((i for i, c in enumerate(self.children)
                          if str(c.value) == text), -1)
            if index >= 0:
                text = self.children[index].text
        self.ui.SetSelection(index)
        if self.editable:
            self.ui.ChangeValue(text)
        self.curr_index.set(index)
        self.curr_text.set(text)

    def _combobox(self, *args, **kwargs):
        node = self.get_node()
        idx = node.ui.GetSelection()
        if node.index_model is not None:
            node.index_model.value = idx
        if node.text_model is not None:
            node.text_model.value = node.children[idx].value if 0 <= idx < len(node.children) else ""
        e = PUIEvent()
        e.value = idx
        node._change(e)

    def _text(self, *args, **kwargs):
        node = self.get_node()
        if not node.editable:
            return
        text = node.ui.GetValue()
        if node.text_model is not None:
            node.text_model.value = text
        e = PUIEvent()
        e.value = text
        node._change(e)

    def addChild(self, idx, child):
        self.ui.Insert(child.text, idx)

    def removeChild(self, idx, child):
        self.ui.Delete(idx)

class ComboBoxItem(PUINode):
    def __init__(self, text, value=None):
        super().__init__()
        self.id(text)
        self.text = text
        if value is None:
            value = text
        self.value = value
