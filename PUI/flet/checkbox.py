from .. import *
from .base import *

class Checkbox(FBase):
    def __init__(self, text, model, value=None):
        super().__init__()
        self.text = text
        self.model = model
        self.value = text if value is None else value

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = checkbox_get(self.model, self.value)
            self.ui.on_change = self._changed
            self.ui.update()
        else:
            self.ui = ft.Checkbox(label=self.text, value=self.model.value, on_change=self._changed)

        super().update(prev)

    def _changed(self, event):
        node = self.get_node()
        checkbox_set(self.model, node.ui.value, self.value)