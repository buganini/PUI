"""Textual pilot and Flet's real session/serialization, without a Flutter client."""
import asyncio
import contextlib
import io
from types import SimpleNamespace
import unittest

from PUI import DummyBinding
from PUI.dom import recur_delete


class TextualTextEditTests(unittest.IsolatedAsyncioTestCase):
    async def test_keyboard_blur_readonly_and_binding(self):
        from PUI.textual import Application, Window, VBox, Button, TextEdit
        model, draft, events = DummyBinding(''), DummyBinding(''), []
        class App(Application):
            readonly = False
            wrap = True
            def content(self):
                with Window():
                    with VBox():
                        self.editor = TextEdit(model, draft, placeholder='Type here',
                                               readonly=self.readonly, wrap=self.wrap)
                        self.editor.input(lambda e: events.append(('input', e.value)))
                        self.editor.change(lambda e: events.append(('change', e.value)))
                        Button('Next')
        root = App()
        async with root.ui.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            editor = root.editor.ui
            editor.focus()
            await pilot.press('a', 'enter', 'b')
            await pilot.pause()
            self.assertEqual(draft.value, 'a\nb')
            self.assertEqual(model.value, '')
            root.wrap = False
            root.sync()
            await pilot.pause()
            self.assertIs(root.editor.ui, editor)
            self.assertEqual(editor.text, 'a\nb')
            await pilot.press('tab')
            await pilot.pause()
            self.assertEqual(model.value, 'a\nb')
            self.assertEqual([e for e in events if e[0] == 'change'], [('change', 'a\nb')])
            previous = list(events)
            model.value = 'external\nvalue'
            root.readonly = True
            root.sync()
            await pilot.pause()
            self.assertEqual(editor.text, model.value)
            editor.focus()
            await pilot.press('x')
            self.assertEqual(editor.text, 'external\nvalue')
            self.assertEqual(events, previous)


class FletTextEditTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_drafts_blur_and_retention(self):
        from flet.messaging.session import Session
        from flet_regression import RecordingConnection
        from PUI.flet import Application, Window, TextEdit
        model, draft, events = DummyBinding(''), DummyBinding(''), []
        class App(Application):
            readonly = False
            def content(self):
                with Window():
                    self.editor = TextEdit(model, draft, readonly=self.readonly, placeholder='Type here')
                    self.editor.input(lambda e: events.append(('input', e.value)))
                    self.editor.change(lambda e: events.append(('change', e.value)))
        session = Session(RecordingConnection(asyncio.get_running_loop()))
        root = App()
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                await root.flet_app(session.page)
            editor = root.editor.ui
            self.assertTrue(editor.multiline)
            self.assertFalse(editor.shift_enter)
            self.assertIsNone(editor.on_submit)
            editor.value = 'a\nb'
            editor.on_change(SimpleNamespace(control=editor))
            self.assertEqual(model.value, '')
            self.assertEqual(draft.value, 'a\nb')
            root.sync()
            self.assertIs(root.editor.ui, editor)
            self.assertEqual(editor.value, 'a\nb')
            editor.on_blur(SimpleNamespace(control=editor))
            editor.on_blur(SimpleNamespace(control=editor))
            self.assertEqual(model.value, 'a\nb')
            self.assertEqual([e for e in events if e[0] == 'change'], [('change', 'a\nb')])
            previous = list(events)
            root.readonly = True
            model.value = 'external'
            root.sync()
            self.assertTrue(editor.read_only)
            self.assertEqual(editor.value, 'external')
            editor.on_change(SimpleNamespace(control=editor))
            self.assertEqual(events, previous)
            with self.assertRaises(NotImplementedError):
                TextEdit(model, wrap=False)
        finally:
            recur_delete(root, root, True)
            await asyncio.sleep(0)
