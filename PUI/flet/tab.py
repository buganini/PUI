from .base import *


class Tabs(FBase):
    NORTH, SOUTH, EAST, WEST = 'n', 's', 'e', 'w'

    def __init__(self, tabposition=NORTH):
        if tabposition not in (self.NORTH, self.SOUTH):
            raise NotImplementedError('Flet TabBar supports NORTH and SOUTH placement')
        self._internal_tag = tabposition
        super().__init__()
        self.tabposition = tabposition

    def update(self, prev):
        if prev and prev.ui is not None:
            self.ui, self.bar, self.view, self.pages = prev.ui, prev.bar, prev.view, prev.pages
        else:
            self.bar = ft.TabBar(tabs=[])
            self.view = ft.TabBarView(controls=[], expand=True)
            controls = [self.bar, self.view] if self.tabposition == self.NORTH else [self.view, self.bar]
            self.ui = ft.Tabs(content=ft.Column(controls, expand=True), length=0)
            self.pages = []
        super().update(prev)

    def preSync(self):
        index = self.ui.selected_index
        self.selected_page = self.pages[index].get_node().ui if 0 <= index < len(self.pages) else None

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
            if page.ui is self.selected_page:
                self.ui.selected_index = i
        self.ui.length = len(self.pages)
        self.ui.selected_index = max(0, min(self.ui.selected_index, len(self.pages) - 1))


class Tab(FBase):
    def __init__(self, label):
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
