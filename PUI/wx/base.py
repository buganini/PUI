from .. import *

import wx

def getWindow(p):
    from .window import Window
    while p:
        if isinstance(p, Window):
            return p.ui
        p = p.parent
    return None

class WxPUIView(PUIView):
    def __init__(self):
        super().__init__()

    def destroy(self, direct):
        if self.ui: # PUIView doesn't have ui
            self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def update(self, prev=None):
        if self.retired_by:
            return
        self.dirty = False
        super().update(prev)
        self.updating = False
        if self.dirty:
            self.update(prev)

class WxBaseWidget(PUINode):
    terminal = True

    def __init__(self):
        super().__init__()

    def destroy(self, direct):
        self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

class WxBaseLayout(PUINode):
    def __init__(self):
        super().__init__()

    def destroy(self, direct):
        # self.ui.Destroy()
        self.ui = None
        super().destroy(direct)

    def addChild(self, idx, child):
        from .layout import Spacer
        if isinstance(child, WxBaseLayout):
            self.ui.Insert(idx, child.outer)
        elif isinstance(child, WxBaseWidget):
            self.ui.Insert(idx, child.outer)
        elif isinstance(child, Spacer):
            self.ui.InsertStretchSpacer(idx, child.layout_weight or 1)
        elif child.children:
            self.addChild(idx, child.children[0])

    def removeChild(self, idx, child):
        from .layout import Spacer
        if isinstance(child, WxBaseLayout):
            self.ui.Detach(idx)
        elif isinstance(child, WxBaseWidget):
            self.ui.Detach(idx)
        elif isinstance(child, Spacer):
            self.ui.Detach(idx)
        else:
            self.removeChild(idx, child.children[0])
