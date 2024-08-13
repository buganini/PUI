from .. import *
from .base import *

class Text(TBase):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.update(self.text)
        else:
            self.ui = widgets.Label(self.text, markup=False)
        super().update(prev)

class Html(Text):
    pui_supported = False

class MarkDown(TBase):
    weak_expand_x = True
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.update(self.text)
        else:
            self.ui = widgets.Markdown(self.text)
        super().update(prev)
