from .base import *


class LinearLayout(FBase):
    def __init__(self):
        super().__init__()
        if not isinstance(self.fparent, LinearLayout):
            self.layout_padding = (11, 11, 11, 11)

    def addChild(self, idx, child):
        self.ui.controls.insert(idx, child.outer)

    def removeChild(self, idx, child):
        self.ui.controls.pop(idx)


class HBox(LinearLayout):
    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Row()
        super().update(prev)


class VBox(LinearLayout):
    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Column()
        super().update(prev)


class Stack(LinearLayout):
    pui_reversed_order = False

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Stack()
        super().update(prev)


class Spacer(FBase):
    pui_terminal = True

    def __init__(self):
        super().__init__()
        self.layout_weight = 1

    def update(self, prev):
        self.ui = prev.ui if prev and prev.ui is not None else ft.Container()
        super().update(prev)
