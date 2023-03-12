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
    Canvas = Tk.TkCanvas
    CanvasText = Tk.TkCanvasText
    CanvasLine = Tk.TkCanvasLine
elif BACKEND=="PySide6":
    from . import PySide6
    Window = PySide6.QtWindow
    HBox = PySide6.QtHBox
    VBox = PySide6.QtVBox
    Label = PySide6.QtLabel
    Button = PySide6.QtButton
    Canvas = PySide6.QtCanvas
    CanvasText = PySide6.QtCanvasText
    CanvasLine = PySide6.QtCanvasLine
elif BACKEND=="Qt5":
    from . import Qt5
    Window = Qt5.QtWindow
    HBox = Qt5.QtHBox
    VBox = Qt5.QtVBox
    Label = Qt5.QtLabel
    Button = Qt5.QtButton
    Canvas = Qt5.QtCanvas
    CanvasText = Qt5.QtCanvasText
    CanvasLine = Qt5.QtCanvasLine
else:
    raise RuntimeError("Unknown Backend")