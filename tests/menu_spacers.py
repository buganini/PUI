"""PUI_TEST_BACKEND=wx env/bin/python -m unittest discover -s tests -p menu_spacers.py.
Run separately for PySide6, wx, tkinter and flet (native GUI required).
"""
import asyncio
import contextlib
import importlib
import io
import os
import unittest
from PUI.dom import recur_delete


class MenuSpacerTests(unittest.IsolatedAsyncioTestCase):
    async def test_ignored_spacers_preserve_menu_indices(self):
        name = os.environ.get('PUI_TEST_BACKEND', 'PySide6')
        ui = importlib.import_module('PUI.' + name)
        calls = []
        class App(ui.Application):
            entries = ['File', '_gap', 'Help']
            generation = 0
            def content(self):
                with ui.Window():
                    with ui.MenuBar(native=False) as self.bar:
                        for key in self.entries:
                            if key.startswith('_'):
                                ui.Spacer().id(key)
                            else:
                                with ui.Menu(key).id(key):
                                    ui.MenuAction('Action').trigger(calls.append, (key, self.generation))
                    ui.Label('Content')
        app = App()
        try:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                if name == 'flet':
                    from flet.messaging.session import Session
                    from flet_regression import RecordingConnection
                    session = Session(RecordingConnection(asyncio.get_running_loop()))
                    await app.flet_app(session.page)
                else:
                    app.sync()
                for generation, entries in enumerate([
                    ['File', '_gap', 'Help'], ['_first', 'Help', '_gap', 'File'],
                    ['Help', 'File'], ['File', '_gap'], ['_gap', 'Help'], [],
                    ['File', '_first', '_gap', 'Help'],
                ]):
                    app.entries, app.generation = entries, generation
                    app.sync()
                    expected = [key for key in entries if not key.startswith('_')]
                    bar = app.bar.ui
                    if name == 'PySide6':
                        actual = [action.text() for action in bar.actions()]
                        for action in bar.actions():
                            action.menu().actions()[0].trigger()
                    elif name == 'wx':
                        import wx
                        actual = [bar.GetMenuLabel(i) for i in range(bar.GetMenuCount())]
                        for i in range(bar.GetMenuCount()):
                            item = bar.GetMenu(i).FindItemByPosition(0)
                            app.children[0].ui.ProcessEvent(wx.CommandEvent(wx.EVT_MENU.typeId, item.GetId()))
                    elif name == 'tkinter':
                        count = 0 if bar.index('end') is None else bar.index('end') + 1
                        actual = [bar.entrycget(i, 'label') for i in range(count)]
                        for i in range(count):
                            bar.nametowidget(bar.entrycget(i, 'menu')).invoke(0)
                    else:
                        actual = [control.content for control in bar.controls]
                        for control in bar.controls:
                            control.controls[0].on_click(None)
                    self.assertEqual(actual, expected)
                    self.assertEqual(calls, [(key, generation) for key in expected])
                    calls.clear()
            self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        finally:
            recur_delete(app, app, True)
            await asyncio.sleep(0)
