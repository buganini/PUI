from .base import *


class ComboBox(FBase):
    def __init__(self, editable=False, index_model=None, text_model=None):
        super().__init__()
        self.editable, self.index_model, self.text_model = editable, index_model, text_model

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Dropdown()
        self.ui.editable = self.editable
        self.ui.on_select = self.on_select
        self.ui.on_text_change = self.on_text_change
        super().update(prev)

    def addChild(self, idx, child):
        self.ui.options.insert(idx, child.ui)

    def removeChild(self, idx, child):
        self.ui.options.pop(idx)

    def postSync(self):
        for i, item in enumerate(self.children):
            item.ui.key, item.ui.text = str(i), item.text
        index, text = -1, ''
        if self.index_model is not None:
            requested = self.index_model.value
            if isinstance(requested, int) and 0 <= requested < len(self.children):
                index = requested
        elif self.text_model is not None:
            text = str(self.text_model.value)
            index = next((i for i, item in enumerate(self.children) if str(item.value) == text), -1)
        self.ui.value = str(index) if index >= 0 else None
        self.ui.text = self.children[index].text if index >= 0 else text if self.editable else ''

    def on_select(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        try:
            index = int(node.ui.value)
        except (TypeError, ValueError):
            index = -1
        if not 0 <= index < len(node.children):
            index = -1
        if node.index_model is not None:
            node.index_model.value = index
        if node.text_model is not None:
            node.text_model.value = node.children[index].value if index >= 0 else ''
        e = PUIEvent()
        e.value = index
        node._change(e)

    def on_text_change(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or not node.editable:
            return
        text = node.ui.text or ''
        if node.ui.value is not None:
            try:
                if node.children[int(node.ui.value)].text == text:
                    return  # Native selected-label updates preserve the item's value.
            except (IndexError, ValueError):
                pass
        if node.text_model is not None:
            node.text_model.value = text
        e = PUIEvent()
        e.value = text
        node._change(e)


class ComboBoxItem(PUINode):
    pui_terminal = True

    def __init__(self, text, value=None):
        super().__init__()
        self.id(text)
        self.text, self.value = text, text if value is None else value

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.DropdownOption()
        self.ui.text = self.text
        super().update(prev)
