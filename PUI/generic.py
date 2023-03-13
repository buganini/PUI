from . import BACKEND

class NotImplementedNode():
    def __init__(self, *args, **kwargs):
        print("Not Implement")
        import traceback
        import inspect
        traceback.print_stack(inspect.currentframe().f_back, 1)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def weight(self, *args):
        return self

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
    TextField = Tk.TkEntry
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
    TextField = PySide6.QtLineEdit
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
    TextField = Qt5.QtLineEdit
elif BACKEND=="flet":
    from . import flet
    Window = flet.FWindow
    HBox = flet.FRow
    VBox = flet.FColumn
    Label = flet.FText
    Button = flet.FElevatedButton
    Canvas = NotImplementedNode
    CanvasText = NotImplementedNode
    CanvasLine = NotImplementedNode
    TextField = flet.FTextField
else:
    raise RuntimeError("Unknown Backend")