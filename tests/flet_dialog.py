"""Real Flet session/controls; file-picker service responses are mocked."""
import asyncio
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch, AsyncMock
import flet as ft
import msgpack
from flet.messaging.session import Session
from flet.controls.context import _context_page
from tests.flet_regression import RecordingConnection
from PUI.flet import Application, Window, Button
from PUI.flet import dialog


class Example(Application):
    def content(self):
        with Window():
            self.button = Button('Choose').click(lambda e: self.choose())


class FletDialogs(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        connection = RecordingConnection(asyncio.get_running_loop())
        self.session = Session(connection)
        msgpack.packb(self.session.get_page_patch(), default=connection.encoder)
        self.token = _context_page.set(self.session.page)
        self.app = Example()
        await self.app.flet_app(self.session.page)

    async def asyncTearDown(self):
        await self.app._shutdown()
        _context_page.reset(self.token)
        self.assertFalse(any(t.name.startswith('pui-flet-callback') for t in threading.enumerate()))

    async def until(self, predicate):
        async with asyncio.timeout(3):
            while not predicate():
                await asyncio.sleep(.01)

    def launch(self, helper):
        self.result = 'pending'
        def choose():
            self.callback_thread = threading.get_ident()
            self.result = helper()
        self.app.choose = choose
        self.app.button._clicked()

    async def active_dialog(self):
        await self.until(lambda: any(d.open for d in self.session.page._dialogs.controls))
        return next(d for d in reversed(self.session.page._dialogs.controls) if d.open)

    async def test_message_results_and_serial_callbacks(self):
        for helper, expected in [(dialog.Information, None), (dialog.Warning, None),
                                 (dialog.Critical, None), (dialog.Confirm, True),
                                 (lambda: dialog.Prompt(default='hello'), '')]:
            self.launch(helper)
            current = await self.active_dialog()
            self.assertNotEqual(self.callback_thread, threading.get_ident())
            calls = []
            self.app.button.get_poster()(lambda: calls.append('next'))
            await asyncio.sleep(.02)
            self.assertEqual(calls, [])
            if isinstance(current.content, ft.Column):
                current.content.controls[1].value = ''
            current.actions[-1].on_click(None)
            await self.until(lambda: self.result != 'pending' and calls)
            self.assertEqual(self.result, expected)
            await self.session.dispatch_event(current._i, 'dismiss', False)

    async def test_dismiss_and_shutdown(self):
        self.launch(dialog.Confirm)
        current = await self.active_dialog()
        await self.session.dispatch_event(current._i, 'dismiss', True)
        await self.until(lambda: self.result != 'pending')
        self.assertIs(self.result, False)
        self.launch(dialog.Prompt)
        await self.active_dialog()
        await self.app._shutdown()
        self.assertIsNone(self.result)

    async def test_file_picker_arguments_results_and_cancel(self):
        page = self.session.page
        page.platform = ft.PagePlatform.MACOS
        page.web = False
        specs = [
            (lambda: dialog.OpenDirectory(directory='/tmp'), 'get_directory_path', '/tmp', '/tmp'),
            (lambda: dialog.OpenFile(types={'Text': ['txt']}), 'pick_files', [SimpleNamespace(path='/tmp/a.txt')], '/tmp/a.txt'),
            (lambda: dialog.OpenFiles(types=['txt']), 'pick_files', [SimpleNamespace(path='/tmp/a.txt'), SimpleNamespace(path='/tmp/b.txt')], ['/tmp/a.txt', '/tmp/b.txt']),
            (lambda: dialog.SaveFile('/tmp/new.txt', types=['txt']), 'save_file', '/tmp/new.txt', '/tmp/new.txt'),
            (dialog.OpenFiles, 'pick_files', [], None),
        ]
        for helper, method, response, expected in specs:
            with patch.object(ft.FilePicker, method, new_callable=AsyncMock, return_value=response) as mock:
                self.launch(helper)
                await self.until(lambda: self.result != 'pending')
                self.assertEqual(self.result, expected)
                args = mock.call_args.kwargs
                if method == 'save_file':
                    self.assertEqual(args['file_name'], 'new.txt')
                    self.assertEqual(args['initial_directory'], '/tmp')
                if args.get('file_type') == ft.FilePickerFileType.CUSTOM:
                    self.assertEqual(args['allowed_extensions'], ['txt'])
                if isinstance(expected, list):
                    self.assertTrue(args['allow_multiple'])

    async def test_wrong_context_and_picker_shutdown(self):
        with self.assertRaises(RuntimeError):
            dialog.Confirm()
        self.session.page.platform = ft.PagePlatform.MACOS
        self.session.page.web = False
        started = asyncio.Event()
        async def pick(*args, **kwargs):
            started.set()
            await asyncio.Future()
        with patch.object(ft.FilePicker, 'pick_files', pick):
            self.launch(dialog.OpenFile)
            await asyncio.wait_for(started.wait(), 3)
            await self.app._shutdown()
            self.assertIsNone(self.result)
