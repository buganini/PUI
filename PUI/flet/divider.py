from .. import *
from .base import *

class Divider(FBase):
    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = ft.Divider()
        self.ui.expand = self.layout_weight

        super().update(prev)
