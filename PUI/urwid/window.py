from .. import *
import urwid
import sys

class UWindow(PUINode):
    @property
    def ui(self):
        return self.children[0].ui

    @ui.setter
    def ui(self, new_ui):
        pass
