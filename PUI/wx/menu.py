from .base import *
from .layout import Spacer


class MenuBar(PUINode):
    pui_outoforder = True

    def __init__(self, *, native=True):
        super().__init__()
        self.native = native

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else wx.MenuBar()
        self.menus = prev.menus if prev else []
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, Spacer):
            self.menus.insert(idx, None)
            return
        if not isinstance(child, Menu):
            raise TypeError('A native wx MenuBar contains Menu or Spacer declarations')
        native_idx = sum(menu is not None for menu in self.menus[:idx])
        self.ui.Insert(native_idx, child.ui, child.text)
        self.menus.insert(idx, child)

    def removeChild(self, idx, child):
        native_idx = sum(menu is not None for menu in self.menus[:idx])
        if self.menus.pop(idx) is not None:
            self.ui.Remove(native_idx)

    def postSync(self):
        native_idx = 0
        for i, menu in enumerate(self.menus):
            if menu is None:
                continue
            menu = menu.get_node()
            self.menus[i] = menu
            self.ui.SetMenuLabel(native_idx, menu.text)
            native_idx += 1


class Menu(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui else wx.Menu()
        self.items = prev.items if prev else []
        super().update(prev)

    def addChild(self, idx, child):
        if isinstance(child, Menu):
            item = wx.MenuItem(self.ui, wx.ID_ANY, child.text, subMenu=child.ui)
        elif isinstance(child, MenuAction):
            item = child.ui
        else:
            raise TypeError('Menu children must be Menu or MenuAction')
        self.ui.Insert(idx, item)
        self.items.insert(idx, (child, item))

    def removeChild(self, idx, child):
        _, item = self.items.pop(idx)
        self.ui.Remove(item)
        if isinstance(child, Menu):
            item.SetSubMenu(None)

    def postSync(self):
        for i, (child, item) in enumerate(self.items):
            child = child.get_node()
            self.items[i] = (child, item)
            item.SetItemLabel(child.text)

    def destroy(self, direct):
        if direct and self.ui:
            self.ui.Destroy()
        self.items = []
        super().destroy(direct)


class MenuAction(PUINode):
    pui_terminal = True

    def __init__(self, text, *, native=True):
        super().__init__()
        self.text = text
        self.native = native
        self.onTriggered = None

    def update(self, prev):
        if prev and prev.ui:
            self.ui = prev.ui
            prev.frame.Unbind(wx.EVT_MENU, handler=prev._triggered, id=self.ui.GetId())
        else:
            parent = self.parent
            while not isinstance(parent, Menu):
                if parent.parent is parent:
                    raise TypeError('MenuAction must be inside a Menu')
                parent = parent.parent
            self.ui = wx.MenuItem(parent.ui, wx.ID_ANY, self.text)
        self.ui.SetItemLabel(self.text)
        self.frame = getWindow(self.parent).GetTopLevelParent()
        self.frame.Bind(wx.EVT_MENU, self._triggered, id=self.ui.GetId())
        super().update(prev)

    def _triggered(self, event=None):
        node = self.get_node()
        if not node.destroyed and node.onTriggered:
            cb, args, kwargs = node.onTriggered
            cb(*args, **kwargs)

    def trigger(self, callback, *cb_args, **cb_kwargs):
        self.onTriggered = (callback, cb_args, cb_kwargs)
        return self

    def destroy(self, direct):
        if self.ui and self.frame:
            self.frame.Unbind(wx.EVT_MENU, handler=self._triggered, id=self.ui.GetId())
        self.frame = None
        self.onTriggered = None
        super().destroy(direct)
