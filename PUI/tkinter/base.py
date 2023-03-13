from .. import *

class TkBaseWidget(PUINode):
    def __init__(self, layout=None, side=None, **kwargs):
        super().__init__()
        self.layout = layout
        self.side = side
        self.kwargs = kwargs

    def destroy(self):
        if self.ui:
            self.ui.destroy()
            self.ui = None