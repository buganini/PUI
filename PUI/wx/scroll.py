from .. import *
from .base import *

class Scroll(PUINode):
    pui_virtual = True
    def __init__(self, vertical=None, horizontal=False):
        self.vertical = vertical
        self.horizontal = horizontal
        super().__init__()
