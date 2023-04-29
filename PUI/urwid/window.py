from .. import *
import urwid
import sys

class UWindow(PUINode):
    def __init__(self, title=None, size=None):
        super().__init__()
        self.title = title
        self.size = size

    @property
    def ui(self):
        return self.children[0].ui

    @ui.setter
    def ui(self, new_ui):
        pass
