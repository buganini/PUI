from .base import *
from .layout import VBox
from ..views import ViewsMixin


class _Page(VBox):
    def putChild(self, idx, child):
        super().putChild(idx, child)
        if child._visible and child.layout_weight is None:
            self.ui.grid_rowconfigure(idx, weight=1)
            self.ui_gridmap.add(idx)


class Views(ViewsMixin, TkBaseWidget):
    expand_x_prio = expand_y_prio = 3
    ttk_style = 'TFrame'

    def _page(self):
        return _Page().layout(padding=0)

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ttk.Frame(self.tkparent.inner)
        self.ui.grid_rowconfigure(0, weight=1)
        self.ui.grid_columnconfigure(0, weight=1)
        super().update(prev)

    def addChild(self, idx, child):
        pass  # Pages are mapped together after reconciliation.

    def removeChild(self, idx, child):
        child.outer.grid_forget()

    def _show_view(self, index):
        for i, page in enumerate(self.children):
            # A virtual child's sync can refresh ancestors before its sibling
            # pages mount. The final Views postSync maps the selected page.
            if page.outer is None:
                continue
            if i == index:
                page.outer.grid(row=0, column=0, sticky='nsew')
            else:
                page.outer.grid_remove()
