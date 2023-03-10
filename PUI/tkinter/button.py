from .. import *

class TkButton(PUINode):
    def __init__(self, text, callback, layout="pack", **kwargs):
        super().__init__()
        self.text = text
        self.callback = callback
        self.layout = layout.lower()
        self.kwargs = kwargs

    def inflate(self):
        import tkinter as tk
        return tk.Button(self.parent.ui, text=self.text, command=self.callback)