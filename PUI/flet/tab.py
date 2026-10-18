from __future__ import annotations
from .. import _typing as _t
from ..common import Side
from .base import *
from ..selection import TabsMixin


class Tabs(TabsMixin, FBase):

    def __init__(self, tabposition: Side = Side.TOP, model: _t.Binding[_t.Any] | None = None) -> None:
        if not isinstance(tabposition, Side):
            raise TypeError('tabposition must be a Side')
        if tabposition not in (Side.TOP, Side.BOTTOM):
            raise NotImplementedError('Flet TabBar supports TOP and BOTTOM placement')
        self._internal_tag = tabposition
        super().__init__(model=model)
        self.tabposition = tabposition
        self.layout_weight = 1

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.bar, self.view, self.pages = prev.ui, prev.bar, prev.view, prev.pages
        else:
            self.bar = ft.TabBar(tabs=[])
            self.view = ft.TabBarView(controls=[], expand=True)
            controls = [self.bar, self.view] if self.tabposition == Side.TOP else [self.view, self.bar]
            self.ui = ft.Tabs(content=ft.Column(controls, expand=True), length=0)
            self.pages = []
        self.ui.on_change = self._tab_changed
        self.bar.on_click = self._tab_changed
        super().update(prev)

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise TypeError('Tabs children must be Tab declarations')
        self.pages.insert(idx, child)
        self.bar.tabs.insert(idx, ft.Tab(label=child.label))
        self.view.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.pages.pop(idx)
        self.bar.tabs.pop(idx)
        self.view.controls.pop(idx)

    def postSync(self):
        for i, page in enumerate(self.pages):
            page = page.get_node()
            self.pages[i] = page
            self.bar.tabs[i].label = page.label
        self.ui.length = len(self.pages)
        # Flet's native Tabs controller requires a nonzero length to render.
        self.ui.visible = bool(self.pages)
        super().postSync()

    def _show_tab(self, index):
        self.ui.selected_index = 0 if index is None else index

    def _tab_changed(self, event):
        self._native_selected(int(event.data))


class Tab(FBase):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.label = label

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Container()
        super().update(prev)

    def addChild(self, idx, child):
        if idx != 0:
            raise ValueError('Tab accepts one content widget or layout')
        self.ui.content = child.outer

    def removeChild(self, idx, child):
        self.ui.content = None
