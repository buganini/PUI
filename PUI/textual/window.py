from .. import *
import sys

class TWindow(PUINode):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    @property
    def ui(self):
        return self.children[0].outer

    @ui.setter
    def ui(self, new_ui):
        pass
