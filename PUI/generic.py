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
elif BACKEND=="Qt":
    from . import Qt
    Window = Qt.QtWindow
    HBox = Qt.QtHBox
    VBox = Qt.QtVBox
    Label = Qt.QtLabel
    Button = Qt.QtButton
    Canvas = Qt.QtCanvas
    CanvasText = Qt.QtCanvasText
    CanvasLine = Qt.QtCanvasLine
else:
    raise RuntimeError("Unknown Backend")