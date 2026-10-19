"""Consumer-facing checks: env/bin/python tests/typing/check.py."""
from typing import assert_type
from PUI import PySide6 as Qt
from PUI import wx as Wx
from PUI import tkinter as Tk
from PUI import textual as Textual
from PUI import flet as Flet
from PUI import web as Web
from PUI import pyodide as Pyodide
from PUI._typing import Binding, Poster
from PUI.interfaces import BaseTableAdapter


class Value:
    value: str = 'text'


def check_widgets() -> None:
    qt: Qt.Button = Qt.Button('Qt').visible(False).style(fontSize=12).click(lambda event: None)
    wx: Wx.Button = Wx.Button('wx').layout(padding=(1, 2)).visible()
    tk: Tk.TextField = Tk.TextField(Value(), placeholder='Text').style(fontSize=14)
    textual: Textual.Label = Textual.Label('terminal').visible()
    flet: Flet.Label = Flet.Label('Flet').flet(size=16).visible()
    web: Web.Label = Web.Label('Web').grid(0, 1).ref('example.label')
    pyodide: Pyodide.Label = Pyodide.Label('Pyodide').layout(weight=1)
    assert_type(Qt.Button('Qt').visible(minWidth=600, maxHeight=800).style(fontSize=12), Qt.Button)
    assert_type(Qt.Window().size(), Binding[tuple[float, float] | None])
    assert_type(Web.VBox().size(), Binding[tuple[float, float] | None])
    assert_type(Web.HVBox(600).layout(weight=1), Web.HVBox)
    assert_type(Textual.VHBox(400, tMinHeight=30).tlayout(weight=1), Textual.VHBox)
    assert_type(Textual.VBox().tsize(), Binding[tuple[float, float] | None])
    assert_type(Textual.Label('T').tlayout(width=20).tstyle(color=0xFF0000).visible(tMinWidth=60), Textual.Label)
    assert_type(Wx.Label('wx').layout(weight=1), Wx.Label)
    assert_type(Tk.TextField(Value()).visible(), Tk.TextField)
    assert_type(Textual.Label('Textual').ref('example.text'), Textual.Label)
    assert_type(Flet.Label('Flet').flet(size=16).visible(), Flet.Label)
    assert_type(Web.Label('Web').style(color=0xff0000), Web.Label)
    assert_type(Pyodide.Label('Pyodide').grid(0, 0), Pyodide.Label)
    binding: Binding[str] = Value()
    post: Poster = qt.get_poster()
    post(lambda: None, delay=50)
    with Qt.VBox() as box:
        typed_box: Qt.VBox = box


def paint(canvas: Web.Canvas) -> None:
    canvas.drawLine(0, 0.5, 100, 100, color=0xff0000)
    canvas.drawPolygon([(0, 0), (10, 0), (10, 10)], fill=0x112233)
    canvas.drawText(0, 0, 'Hello', size=14)


class Rows(BaseTableAdapter):
    def rowCount(self) -> int:
        return 1
    def columnCount(self) -> int:
        return 1
    def data(self, row: int, col: int) -> str:
        return 'value'


def start_agents(qt: Qt.Application, wx: Wx.Application, tk: Tk.Application,
                 flet: Flet.Application, textual: Textual.Application,
                 web: Web.Application, pyodide: Pyodide.Application) -> None:
    qt.start(codex={})
    wx.start(claude={"key": "example", "model": "model", "effort": "high"})
    tk.run(codex={"effort": "high"})
    flet.run(claude={})
    textual.start(codex=False)
    web.start(codex={"model": "model"}, claude=None)
    pyodide.run(codex={})
