from .. import *
from .base import *

class FText(FBase):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            self.ui.update()
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)

class FHtml(FBase):
    supported = False
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            self.ui.update()
        else:
            self.ui = ft.Text(self.text, expand=self.layout_weight)

class FMarkDown(FBase):
    supported = False
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.ui.value = self.text
            self.ui.update()
        else:
            self.ui = ft.Markdown(self.text, expand=self.layout_weight, auto_follow_links=True)
