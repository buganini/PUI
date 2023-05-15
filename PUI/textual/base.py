from .. import *
from textual import widgets, containers

class TBase(PUINode):
    def destroy(self, direct):
        self.ui.remove()
        return super().destroy(direct)