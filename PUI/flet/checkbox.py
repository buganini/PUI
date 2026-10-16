from .. import *
from .base import *

class Checkbox(FBase):
    def __init__(self, text, model, value=None, *, disabled=False):
        super().__init__()
        self.text = text
        self.disabled = disabled
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = checkbox_get(self.model, self.value)
            self.ui.on_change = self._changed
        else:
            self.ui = ft.Checkbox(label=self.text, value=checkbox_get(self.model, self.value), on_change=self._changed)

        self.ui.label = self.text
        super().update(prev)
        self.ui.disabled = self.flet_params.get('disabled', self.disabled)

    def _changed(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        checkbox_set(node.model, node.ui.value, node.value)
        node._clicked()