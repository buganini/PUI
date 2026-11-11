from __future__ import annotations
from .. import _typing as _t
from .. import *
from .base import *
class Button(TkBaseWidget):
    ttk_style = "TButton"
    def __init__(self, text: _t.Any = '', *, icon: _t.Any = None, disabled: bool = False) -> None:
        super().__init__()
        self.text = text
        self.icon = icon
        self.disabled = disabled

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            self._photo = prev._photo
            self.ui.config(text = self.text)
            self.ui.config(command = self._clicked)
        else:
            self.ui = ttk.Button(self.tkparent.inner, text=self.text, width=0, command=self._clicked)
            self._photo = None
        if self.icon is not None:
            self._photo = tk.PhotoImage(file=str(self.icon))
            self.ui.configure(image=self._photo, compound='left' if self.text else 'image')
        elif self._photo is not None:
            self.ui.configure(image='', compound='none')
            self._photo = None
        self.ui.configure(state='disabled' if self.disabled else 'normal')
        super().update(prev)
