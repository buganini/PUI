from .. import *
from .base import *

class RadioButton(FBase):
    def __init__(self, text, value, model, *, disabled=False):
        super().__init__()
        self.text = text
        self.disabled = disabled
        self.value = value
        self.model = model

    def update(self, prev):
        if prev and prev.ui:
            self.radio = prev.radio
            self.ui = prev.ui
            self.radio.value = str(self.value)
            self.ui.value = str(self.model.value)
            self.ui.on_change = self._changed
        else:
            self.radio = ft.Radio(value=str(self.value), label=self.text)
            self.ui = ft.RadioGroup(content=self.radio, on_change=self._changed)
        self.radio.label = self.text
        self.ui.value = str(self.model.value)
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', self.disabled)

    def _changed(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        if event.control.value is not None:
            node.model.value = node.value
            node._clicked()
