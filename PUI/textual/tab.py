from itertools import count
from rich.text import Text

from .base import *
from .layout import VBox
from ..selection import TabsMixin


_page_ids = count()


class Tabs(TabsMixin, TBase):
    NORTH, SOUTH, EAST, WEST = 'n', 's', 'e', 'w'
    expand_x_prio = 2
    expand_y_prio = 2

    def __init__(self, tabposition=NORTH, model=None):
        if tabposition not in (self.NORTH, self.SOUTH):
            raise NotImplementedError('Textual Tabs supports NORTH and SOUTH placement')
        super().__init__(model=model)
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.bar, self.frame = prev.ui, prev.bar, prev.frame
        else:
            self.ui = containers.Vertical()
            self.bar = widgets.Tabs()
            self.frame = widgets.ContentSwitcher()
            self.frame.styles.height = '1fr'
        self.bar.puinode = self
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        if self.bar.parent is None:
            self.ui.mount(self.bar, self.frame)
        if child.outer.parent is not self.frame:
            child.outer.display = False
            self.frame.mount(child.outer)

    def removeChild(self, idx, child):
        pass  # Actual deletion happens in destroy(); keyed moves retain pages.

    def _show_tab(self, index):
        self._selection_status['pending'] = True
        self.ui.call_after_refresh(self._apply_tabs)

    async def _apply_tabs(self):
        node = self.get_node()
        if node.destroyed or node.ui is None:
            return
        if node.bar.parent is None:
            await node.ui.mount(node.bar, node.frame)
        if node.tabposition == self.NORTH:
            node.ui.move_child(node.bar, before=node.frame)
        else:
            node.ui.move_child(node.bar, after=node.frame)
        pages = node.children
        wanted = {p.ui.id for p in pages}
        with node.bar.prevent(widgets.Tabs.TabActivated, widgets.Tabs.Cleared):
            for tab in list(node.bar.query(widgets.Tab)):
                if tab.id not in wanted:
                    await node.bar.remove_tab(tab)
            for index, page in enumerate(pages):
                node.frame.move_child(page.ui, before=index)
                tab = node.bar.get_tab(page.ui.id)
                if tab is None:
                    tab = widgets.Tab(Text(str(page.label)), id=page.ui.id)
                    await node.bar.add_tab(tab)
                else:
                    tab.label = Text(str(page.label))
                tab.parent.move_child(tab, before=index)
            index = node._selected_index()
            current = None if index is None else pages[index].ui.id
            for page in pages:
                page.ui.display = page.ui.id == current
            node.frame.current = current
            node.bar.active = current or ''
        node._selection_status['applied'] = index
        node._selection_status['pending'] = False

    def _tab_activated(self, event):
        node = self.get_node()
        if node.destroyed or node.ui is None or node._selection_status.get('pending'):
            return
        if event.tab is None or event.tab.id != node.bar.active:
            return
        index = next((i for i, page in enumerate(node.children)
                      if page.ui.id == event.tab.id), None)
        node._native_selected(index)


class Tab(VBox):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def update(self, prev):
        super().update(prev)
        if self.ui.id is None:
            self.ui.id = f'pui-tab-{next(_page_ids)}'
