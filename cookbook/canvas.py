from PUI.PySide6 import *

@PUI
def CanvasExample():
    with Canvas(bgColor=0xFFFFFF):
        CanvasText(20, 60, "PUI")
        CanvasPolyline(((20,20),(30,30),(40,10),(50,50)), color=0xFFFF00)
