from .. import *
from .base import *

class TkApplication(PUIView):
    def redraw(self):
        if self.ui:
            self.ui.after(0, self.update)
        else:
            self.update()

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
        child.destroy()

    def start(self):
        self.ui.mainloop()
