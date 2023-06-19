from .. import *
from .base import *

class RadioButton(FBase):
    def __init__(self, text, value, model):
        super().__init__()
        self.text = text
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.radio = prev.radio
            self.ui = prev.ui
            self.radio.value = self.value
            self.ui.value = self.model.value
            self.ui.on_change = self._changed
            self.ui.update()
        else:
            self.radio = ft.Radio(value=self.value, label=self.text)
            self.ui = ft.RadioGroup(content=self.radio, on_change=self._changed)
        super().update(prev)

    def _changed(self, event):
        node = self.get_node()
        if event.control.value:
            self.model.value = node.value
