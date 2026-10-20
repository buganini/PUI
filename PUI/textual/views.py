from .base import *
from .layout import VBox
from ..views import ViewsMixin


class _Page(VBox):
    def update(self, prev):
        super().update(prev)
        if self.ui.id is None:
            # PUI IDs may contain characters that Textual's CSS IDs forbid.
            self.ui.id = 'pui-view-' + self._id.encode('utf-8').hex()


class Views(ViewsMixin, TBase):
    expand_x_prio = 2
    expand_y_prio = 2

    def _page(self):
        return _Page().tLayout(padding=0)

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else widgets.ContentSwitcher()
        super().update(prev)

    def addChild(self, idx, child):
        if child.outer.parent is not self.ui:
            child.outer.display = False
            self.ui.mount(child.outer, before=idx if idx < len(self.ui.children) else None)

    def removeChild(self, idx, child):
        # The shared DOM also removes nodes during a keyed move. Actual deletion
        # is handled by destroy(); final order is applied after native mounting.
        pass

    def _show_view(self, index):
        self.ui.call_after_refresh(self._apply_selection)

    def _apply_selection(self):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        current = None
        for index, page in enumerate(node.children):
            node.ui.move_child(page.ui, before=index)
            page.ui.display = page._id == node.model.value
            if page.ui.display:
                current = page.ui.id
        node.ui.current = current
