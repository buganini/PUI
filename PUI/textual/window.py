from .. import *
import sys

class TWindow(PUINode):
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
        self.title = title
        self.size = size
        self.curr_size = None
        self.maximize = maximize
        self.curr_maximize = None
        self.fullscreen = fullscreen
        self.curr_fullscreen = None

    @property
    def ui(self):
        return self.children[0].outer

    @ui.setter
    def ui(self, new_ui):
        pass
