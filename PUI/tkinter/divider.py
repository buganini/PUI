from .base import *
from .layout import HBox


class Divider(TkBaseWidget):
    ttk_style = 'TSeparator'

    def update(self, prev):
        vertical = bool(getattr(self.tkparent, 'container_x', isinstance(self.tkparent, HBox)))
        self.expand_x_prio = 0 if vertical else 1
        self.expand_y_prio = 1 if vertical else 0
        self.ui = prev.ui if prev and prev.ui is not None else ttk.Separator(self.tkparent.inner)
        self.ui.configure(orient=tk.VERTICAL if vertical else tk.HORIZONTAL)
        super().update(prev)
