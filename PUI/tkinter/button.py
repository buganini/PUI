from .. import *

class TkButton(PUINode):
    def __init__(self, text, callback):
        super().__init__()
        self.text = text
        self.callback = callback

    def inflate(self):
        import tkinter as tk
        return tk.Button(self.parent.ui, text=self.text, command=self.callback)