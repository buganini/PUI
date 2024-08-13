from .. import *
from .base import *

class Text(FBase):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            try:
                self.ui.update()
            except:
                pass
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)
        super().update(prev)

class Html(FBase):
    pui_supported = False
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            try:
                self.ui.update()
            except:
                pass
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)
        super().update(prev)

class MarkDown(FBase):
    pui_supported = False
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            try:
                self.ui.update()
            except:
                pass
        else:
            self.ui = ft.Markdown(self.text, expand=self.layout_weight, auto_follow_links=True)
        super().update(prev)
