from . import BACKEND

Window = None
HBox = None
VBox = None
Label = None
Button = None

if BACKEND=="Tk":
    from . import tkinter as Tk
    Window = Tk.TkWindow
    HBox = Tk.TkHBox
    VBox = Tk.TkVBox
    Label = Tk.TkLabel
    Button = Tk.TkButton
elif BACKEND=="Qt":
    from . import Qt
    Window = Qt.QtWindow
    HBox = Qt.QtHBox
    VBox = Qt.QtVBox
    Label = Qt.QtLabel
    Button = Qt.QtButton
