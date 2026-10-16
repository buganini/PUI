from .base import *
from .layout import HBox


class Divider(TkBaseWidget):
    ttk_style = 'TSeparator'

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ttk.Separator(self.tkparent.inner)
        self.ui.configure(orient=tk.VERTICAL if isinstance(self.tkparent, HBox) else tk.HORIZONTAL)
        super().update(prev)
