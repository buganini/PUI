"""State-driven Modal contracts across browser, Flet and Textual."""
import asyncio
import importlib
import unittest
from types import SimpleNamespace


def demo(UI):
    class Demo(UI.Application):
        show = True
        version = 'one'
        def __init__(self):
            super().__init__()
            self.state = UI.State()
            self.state.open = False
            self.events = []
        def content(self):
            with UI.Window():
                with UI.VBox():
                    UI.Label('outside')
                    if self.show:
                        with UI.Modal(self.state('open'), offValue=False, title='Test').open(self.events.append,'open').close(self.events.append,'close') as self.modal:
                            with UI.VBox():
                                self.label = UI.Label(self.version)
                                UI.Button('Close').click(lambda *args: setattr(self.state,'open',False))
    return Demo()


class BrowserModal(unittest.IsolatedAsyncioTestCase):
    async def test_state_retention_close_event_and_removal(self):
        UI=importlib.import_module('PUI.web')
        from PUI.web.runtime import Runtime
        runtime=Runtime(asyncio.get_running_loop());self.addCleanup(runtime.close)
        app=runtime.app=demo(UI);app.sync();runtime.snapshot()
        self.assertEqual(app.events,[])
        app.state.open=True;app.sync();snapshot=runtime.snapshot()
        modal=app.modal;ui=modal.ui
        self.assertTrue(modal.properties()['open'])
        self.assertEqual(app.events,['open'])
        app.version='two';app.sync();runtime.snapshot()
        self.assertIs(app.modal.ui,ui)
        self.assertEqual(app.events,['open'])
        body=dict(node_id=ui.id,event='dismiss',token=ui.events['dismiss'],observed_render_rev=0,data={})
        self.assertEqual(runtime.action('event',body),('processed',None))
        self.assertFalse(app.state.open)
        app.sync();runtime.snapshot()
        self.assertEqual(app.events,['open','close'])
        self.assertEqual(runtime.action('event',body)[0],'stale')
        app.state.open=True;app.sync();runtime.snapshot()
        app.show=False;app.sync();runtime.snapshot()
        self.assertEqual(app.events,['open','close','open','close'])


class FletModal(unittest.IsolatedAsyncioTestCase):
    async def test_state_retention_and_dismiss(self):
        from flet.messaging.session import Session
        from tests.flet_regression import RecordingConnection
        from PUI.dom import recur_delete
        UI=importlib.import_module('PUI.flet')
        session=Session(RecordingConnection(asyncio.get_running_loop()))
        app=demo(UI)
        await app.flet_app(session.page)
        try:
            dialog=app.modal.dialog
            app.state.open=True;app.sync()
            self.assertTrue(dialog.open)
            self.assertIn(dialog,session.page.overlay)
            self.assertEqual(app.events,['open'])
            app.version='two';app.sync()
            self.assertIs(app.modal.dialog,dialog)
            await dialog.on_dismiss(SimpleNamespace(data=None))
            app.sync()
            self.assertFalse(app.state.open)
            self.assertEqual(app.events,['open','close'])
            app.state.open=True;app.sync()
            app.show=False;app.sync()
            self.assertNotIn(dialog,session.page.overlay)
            self.assertEqual(app.events,['open','close','open','close'])
        finally:
            recur_delete(app,app,True)


    async def test_escape_topmost_reopen_and_imperative_guard(self):
        import PUI.flet as UI
        from flet.messaging.session import Session
        from tests.flet_regression import RecordingConnection
        from PUI.dom import recur_delete
        class Demo(UI.Application):
            def setup(self):
                self.state = UI.State()
                self.state.outer = self.state.inner = False
                self.closed = []
            def content(self):
                with UI.Window():
                    with UI.Modal(self.state('outer'), offValue=False).close(self.closed.append, 'outer') as self.outer_modal:
                        with UI.VBox():
                            UI.Label('outer')
                            with UI.Modal(self.state('inner'), offValue=None).close(self.closed.append, 'inner') as self.inner_modal:
                                UI.Label('inner')
        app = Demo()
        session = Session(RecordingConnection(asyncio.get_running_loop()))
        await app.flet_app(session.page)
        async def key(value='Escape'):
            await session.page.on_keyboard_event(SimpleNamespace(key=value))
            app.sync()
        try:
            await key()  # No modal open.
            app.state.outer = app.state.inner = True
            app.sync()
            outer, inner = app.outer_modal.dialog, app.inner_modal.dialog
            app.sync()  # Retain native dialogs and replace declarative nodes.
            self.assertIs(app.inner_modal.dialog, inner)
            self.assertEqual(app._modal_stack, [outer, inner])
            await key('Enter')
            self.assertTrue(inner.open)
            pending = asyncio.get_running_loop().create_future()
            app._dialogs[pending] = 'prompt'
            await key()
            self.assertTrue(inner.open)
            del app._dialogs[pending]
            await key()
            self.assertIsNone(app.state.inner)
            self.assertTrue(app.state.outer)
            self.assertEqual(app.closed, ['inner'])
            self.assertEqual(app._modal_stack, [outer])
            await app.inner_modal._on_dismiss(SimpleNamespace(data=False))
            self.assertEqual(app.closed, ['inner'])
            await key()
            self.assertFalse(app.state.outer)
            self.assertEqual(app.closed, ['inner', 'outer'])
            app.state.outer = app.state.inner = True
            app.sync()
            self.assertEqual(app._modal_stack, [outer, inner])
            app.state.outer = False
            app.sync()
            self.assertEqual(app._modal_stack, [])
            self.assertTrue(app.state.inner)  # Hidden by ancestor, not dismissed.
            app.state.outer = True
            app.sync()
            self.assertEqual(app._modal_stack, [outer, inner])
        finally:
            recur_delete(app, app, True)
            self.assertEqual(app._modal_stack, [])
            await app._shutdown()


class TextualModal(unittest.IsolatedAsyncioTestCase):
    async def test_state_content_escape_and_reopen(self):
        UI=importlib.import_module('PUI.textual')
        app=demo(UI)
        async with app.ui.run_test(size=(90,30)) as pilot:
            await pilot.pause()
            app.state.open=True
            await pilot.pause()
            self.assertIs(app.ui.screen,app.modal.screen)
            self.assertIsNotNone(app.label.ui)
            widget=app.label.ui
            app.version='two';app.sync();await pilot.pause()
            self.assertIs(app.label.ui,widget)
            await pilot.press('escape');await pilot.pause()
            self.assertFalse(app.state.open)
            self.assertEqual(app.events,['open','close'])
            app.state.open=True;await pilot.pause()
            self.assertIs(app.label.ui,widget)
            app.show=False;app.sync();await pilot.pause()
            self.assertEqual(app.events,['open','close','open','close'])


class NestedTextualModal(unittest.IsolatedAsyncioTestCase):
    async def test_remove_unopened_nested_modal(self):
        import PUI.textual as UI
        class Demo(UI.Application):
            show = True
            def setup(self):
                self.state = UI.State()
                self.state.open = False
            def content(self):
                with UI.Window():
                    if self.show:
                        with UI.Modal(self.state('open')):
                            with UI.Modal(self.state('open')):
                                UI.Label('Never mounted')
        app = Demo()
        async with app.ui.run_test() as pilot:
            await pilot.pause()
            app.show = False
            app.sync()
            await pilot.pause()

    async def test_nested_parent_close_and_grid_mount(self):
        import PUI.textual as UI
        class Demo(UI.Application):
            def __init__(self):
                super().__init__();self.state=UI.State();self.state.a=False;self.state.b=True
            def content(self):
                with UI.Window():
                    with UI.Grid():
                        UI.Label('outside').grid(row=0,column=0)
                        with UI.Modal(self.state('a'),offValue=False) as self.a:
                            with UI.VBox():
                                UI.Label('a')
                                with UI.Modal(self.state('b'),offValue=False) as self.b:
                                    UI.Label('b')
        app=Demo()
        async with app.ui.run_test() as pilot:
            await pilot.pause()
            app.state.a=True;await pilot.pause();await pilot.pause()
            self.assertIs(app.ui.screen,app.b.screen)
            app.state.a=False;await pilot.pause();await pilot.pause()
            self.assertNotIn(app.a.screen,app.ui.screen_stack)
            self.assertNotIn(app.b.screen,app.ui.screen_stack)
            app.state.a=True;await pilot.pause();await pilot.pause()
            self.assertIs(app.ui.screen,app.b.screen)
            await pilot.press('escape');await pilot.pause()
            self.assertIs(app.ui.screen,app.a.screen)
