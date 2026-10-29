"""env/bin/python -m unittest discover -s tests -p menu_tk_flet.py (Tk needs GUI)."""
import asyncio
import contextlib
import io
import unittest
from PUI.dom import recur_delete


def example(backend, calls):
    class Demo(backend.Application):
        names = ('first', 'second')
        generation = 0
        shown = True
        def content(self):
            with backend.Window() as self.window:
                if self.shown:
                    with backend.MenuBar(native=False).id('bar') as self.bar:
                        with backend.Menu('File').id('file') as self.menu:
                            for name in self.names:
                                backend.MenuAction(name, native=False).id(name).trigger(calls.append, (name, self.generation))
                            with backend.Menu('Nested') as self.nested:
                                backend.MenuAction('Deep').trigger(calls.append, 'deep')
                backend.Label('Body').id('body')
    return Demo()


class TkMenus(unittest.TestCase):
    def test_retained_menus(self):
        from PUI import tkinter as backend
        calls = []
        app = example(backend, calls)
        try:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                app.sync()
                app.ui.update()
                menu = app.menu.ui
                for generation in range(5):
                    app.generation = generation
                    app.names = ('second', 'first') if generation % 2 else ('first', 'second')
                    app.sync()
                    self.assertIs(app.menu.ui, menu)
                    self.assertEqual(menu.entrycget(0, 'label'), app.names[0])
                    menu.invoke(0)
                    self.assertEqual(calls[-1], (app.names[0], generation))
                    self.assertEqual(len(menu._tclCommands), 2)
                app.nested.ui.invoke(0)
                self.assertEqual(calls[-1], 'deep')
                app.names = ('second',)
                app.sync()
                self.assertEqual(menu.index('end'), 1)
                app.shown = False
                app.sync()
                self.assertEqual(str(app.window.ui.cget('menu')), '')
                app.shown = True
                app.sync()
                self.assertTrue(str(app.window.ui.cget('menu')))
            self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        finally:
            recur_delete(app, app, True)


class FletMenus(unittest.IsolatedAsyncioTestCase):
    async def test_retained_menus(self):
        from PUI import flet as backend
        from flet.messaging.session import Session
        from flet_regression import RecordingConnection
        calls = []
        app = example(backend, calls)
        session = Session(RecordingConnection(asyncio.get_running_loop()))
        async def flush():
            await asyncio.sleep(0)
            await app._callback_queue.join()
        try:
            with contextlib.redirect_stdout(io.StringIO()) as output:
                await app.flet_app(session.page)
                menu = app.menu.ui
                old_callback = menu.controls[0].on_click
                for generation in range(5):
                    app.generation = generation
                    app.names = ('second', 'first') if generation % 2 else ('first', 'second')
                    app.sync()
                    self.assertIs(app.menu.ui, menu)
                    self.assertEqual(menu.controls[0].content, app.names[0])
                    menu.controls[0].on_click(None)
                    await flush()
                    self.assertEqual(calls[-1], (app.names[0], generation))
                old_callback(None)
                await flush()
                self.assertEqual(calls[-1], ('first', 4))
                app.nested.ui.controls[0].on_click(None)
                await flush()
                self.assertEqual(calls[-1], 'deep')
                app.names = ('second',)
                app.sync()
                self.assertEqual(len(menu.controls), 2)
                count = len(calls)
                old_callback(None)
                self.assertEqual(len(calls), count)
                app.shown = False
                app.sync()
                self.assertEqual(len(session.page.controls), 1)
                app.shown = True
                app.sync()
                self.assertEqual(len(session.page.controls), 2)
                self.assertEqual(app.bar.outer.expand, 0)
            self.assertNotIn('<ERROR', output.getvalue(), output.getvalue())
        finally:
            await app._shutdown()
            recur_delete(app, app, True)
            await asyncio.sleep(0)
