from .. import *
import sys

class Window(PUINode):
    pui_virtual = True
    def __init__(self, title=None, size=None, maximize=None, fullscreen=None):
        super().__init__()
