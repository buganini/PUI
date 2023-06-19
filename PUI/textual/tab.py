from .. import *
from .base import *

class Tabs(TBase):
    NORTH = "n"
    SOUTH = "s"
    EAST = "e"
    WEST = "w"
    terminal = False
    def __init__(self, tabposition=NORTH):
        super().__init__()
        self.tabposition = tabposition
        self.tabs = None
        self.current_tab = None
        self._dirty = False

    def update(self, prev):
        if prev and prev.ui:
            self.current_tab = prev.current_tab
            self.ui = prev.ui
            self.tabhost = prev.tabhost
            self.frame = prev.frame
            self.tabs = prev.tabs
        else:
            self.ui = containers.Vertical()
            self.tabhost = containers.Container()
            self.frame = containers.Container()
            self.ui.mount(self.tabhost)
            self.ui.mount(self.frame)
        super().update(prev)

    def postUpdate(self):
        pass

    def addChild(self, idx, child):
        if not isinstance(child, Tab):
            raise RuntimeError("Tabs can only contain Tab")
        self._dirty = True
        child.outer.display = False
        self.frame.mount(child.outer, before=idx)


    def removeChild(self, idx, child):
        self.ui.removeTab(idx)
        self._dirty = True
        child.tremove()

    def postSync(self):
        if self._dirty:
            if self.tabs:
                self.tabs.remove()
            tabs = []
            for c in self.children:
                tab = widgets.Tab(c.label)
                tab.puinode = c
                tabs.append(tab)
            self.tabs = widgets.Tabs(*tabs)
            self.tabs.puinode = self
            self.tabhost.mount(self.tabs)
            self._dirty = False
        super().postSync()

    def _tab_activated(self, event: widgets.Tabs.TabActivated):
        print(event.tab)
        node = self.get_node()
        if node.current_tab:
            node.current_tab.outer.display = False
        if event.tab:
            tab = event.tab.puinode.get_node()
            tab.outer.display = True
            self.current_tab = tab

class Tab(PUINode):
    def __init__(self, label):
        super().__init__()
        self.label = label

    def addChild(self, idx, child):
        if idx > 0:
            raise RuntimeError("Tab can only have one child")
