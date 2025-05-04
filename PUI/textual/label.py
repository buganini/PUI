from .. import *
from .base import *

class Label(TBase):
    def __init__(self, text, selectable=False):
        super().__init__()
        self.widget = None
        self.text = text

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self.widget = prev.widget
        else:
            self.ui = containers.Container()
        if self._onClicked:
            if self.widget is None or not isinstance(self.widget, widgets.Button):
                if self.widget:
                    self.widget.remove()
                self.widget = widgets.Button(self.text)
                self.widget.set_styles("border-top: none; border-bottom: none;")
                self.widget.puinode = self
            else:
                self.widget.label = self.text
        else:
            if self.widget is None or not isinstance(self.widget, widgets.Label):
                if self.widget:
                    self.widget.remove()
                self.widget = widgets.Label(self.text, markup=False)
            else:
                self.widget.update(self.text)
        super().update(prev)

    def postUpdate(self):
        super().postUpdate()
        self.ui.mount(self.widget)
