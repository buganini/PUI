from .. import *
from .base import *

class Application(TPUIView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.theme = None

    def tkinter(self, theme=None, **kwargs):
        super().tkinter(**kwargs)
        if theme:
            self.theme = theme
        return self

    def update(self, prev=None):
        if prev and prev.ui:
            self.ui = prev.ui
        else:
            self.ui = tk.Tk()
            ttkStyle = ttk.Style(self.ui)
            if self.theme:
                ttkStyle.theme_use(self.theme)
            self.ui.withdraw()

        super().update(prev)

    def addChild(self, idx, child):
        pass

    def removeChild(self, idx, child):
        pass

    def start(self):
        self.ui.mainloop()
