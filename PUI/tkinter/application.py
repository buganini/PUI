from .. import *
from .base import *
import functools

class TkApplication(PUIView):
    def redraw(self):
        if self.ui:
            self.ui.after(0, functools.partial(self.update, redraw=True))
        else:
            self.update(redraw=True)

    def update(self, prev=None):
        if prev and hasattr(prev, "ui"):
            self.ui = prev.ui
        else:
            self.ui = tk.Tk()
            self.ui.withdraw()

        super().update(prev)

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def start(self):
        self.ui.mainloop()
