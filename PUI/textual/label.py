from .. import *
from .base import *

class TLabel(TBase):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def update(self, prev):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
            self.widget = prev.widget
        else:
            self.ui = containers.Container()
            self.ui.set_styles("width: auto; height: auto;")
            self.widget = None
        if self.onClicked:
            if self.widget is None or not isinstance(self.widget, widgets.Button):
                if self.widget:
                    self.widget.remove()
                self.widget = widgets.Button(self.text)
                self.widget.set_styles("height: 1; border-top: none; border-bottom: none; min-width: 0;")
                self.widget.puinode = self
                self.ui.mount(self.widget)
            else:
                self.widget.label = self.text
        else:
            if self.widget is None or not isinstance(self.widget, widgets.Label):
                if self.widget:
                    self.widget.remove()
                self.widget = widgets.Label(self.text, markup=False)
                self.ui.mount(self.widget)
            else:
                self.widget.update(self.text)
