from .. import *

class TkButton(PUINode):
    def __init__(self, text):
        super().__init__()
        self.text = text

    def inflate(self):
        import tkinter as tk
        return tk.Button(self.parent.ui, text=self.text)