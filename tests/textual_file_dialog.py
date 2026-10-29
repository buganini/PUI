"""Native Textual pilot coverage for all four synchronous file helpers."""
import asyncio
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from PUI.textual import Application, Window, VBox, Button, Label, State, OpenDirectory, OpenFile, OpenFiles, SaveFile
from PUI.textual.file_dialog import FileDialog, _listing
from textual.widgets import Input, OptionList, SelectionList, Button as TButton, Static

class Example(Application):
    def setup(self):
        self.state = State()
        self.state.result = 'idle'
        self.result = 'pending'
    def content(self):
        with Window(), VBox():
            Button('Choose').click(self.choose)
            Label(str(self.state.result))
    def choose(self, event):
        self.result = self.helper(**self.arguments)
        self.state.result = repr(self.result)

class FileDialogTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root/'folder').mkdir()
        (self.root/'folder'/'nested.txt').write_text('nested')
        (self.root/'a.txt').write_text('a')
        (self.root/'b.txt').write_text('b')
        (self.root/'other.csv').write_text('c')
    def app(self, helper, **kwargs):
        app = Example()
        app.helper, app.arguments = helper, dict(dir=self.root, **kwargs)
        return app
    async def ready(self, app):
        async def wait():
            while not isinstance(app.ui.screen, FileDialog) or app.ui.screen.busy or not app.ui.screen.entries:
                await asyncio.sleep(.01)
        await asyncio.wait_for(wait(), 3)
        return app.ui.screen
    async def open(self, app):
        app.children[0].children[0].children[0].ui.press()
        return await self.ready(app)
    async def settled(self, screen):
        async def wait():
            while screen.busy:
                await asyncio.sleep(.01)
        await asyncio.wait_for(wait(), 3)
    async def test_open_file_filter_and_keyboard(self):
        app = self.app(OpenFile, types=['txt'])
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            self.assertEqual([p.name for p,d in screen.entries], ['folder','a.txt','b.txt'])
            rows = screen.query_one(OptionList); rows.focus(); rows.highlighted = 1
            await pilot.press('enter'); await pilot.pause()
            screen.query_one('#file-confirm',TButton).press(); await pilot.pause()
            self.assertEqual(app.result, str(self.root/'a.txt'))
    async def test_multi_selection_and_cancel(self):
        app = self.app(OpenFiles)
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            rows = screen.query_one(SelectionList); rows.focus(); rows.highlighted = 1
            await pilot.press('space','down','space'); await pilot.pause()
            self.assertEqual(set(screen.selected),{str(self.root/'a.txt'),str(self.root/'b.txt')})
            screen.query_one('#file-confirm',TButton).press(); await pilot.pause()
            self.assertEqual(set(app.result),{str(self.root/'a.txt'),str(self.root/'b.txt')})
            screen = await self.open(app)
            await pilot.press('escape'); await pilot.pause()
            self.assertIsNone(app.result)
    async def test_multi_selection_across_directories(self):
        app = self.app(OpenFiles)
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            rows = screen.query_one(SelectionList)
            rows.toggle(str(self.root/'a.txt')); await pilot.pause()
            rows.toggle(str(self.root/'folder')); await pilot.pause(); await self.settled(screen)
            rows.toggle(str(self.root/'folder'/'nested.txt')); await pilot.pause()
            self.assertEqual(len(screen.selected), 2)
            screen.query_one('#file-up',TButton).press(); await pilot.pause(); await self.settled(screen)
            self.assertIn(str(self.root/'a.txt'), rows.selected)
            rows.toggle(str(self.root/'a.txt')); await pilot.pause()
            self.assertEqual(screen.selected, [str(self.root/'folder'/'nested.txt')])
            rows.toggle(str(self.root/'b.txt')); await pilot.pause()
            screen.query_one('#file-confirm',TButton).press(); await pilot.pause()
            self.assertEqual(app.result, [str(self.root/'folder'/'nested.txt'), str(self.root/'b.txt')])

    async def test_folder_rows_have_no_checkbox_and_still_navigate(self):
        app = self.app(OpenFiles)
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            await pilot.pause()
            rows = screen.query_one(SelectionList)
            folder_line = rows.render_line(0).text
            file_line = rows.render_line(1).text
            self.assertTrue(folder_line.startswith('    ▸ folder'), folder_line)
            self.assertFalse(file_line[:4].isspace(), file_line)
            # Clicking even the blank checkbox gutter must open the folder.
            await pilot.click(rows, offset=(rows.gutter.left, rows.gutter.top))
            await pilot.pause(); await self.settled(screen)
            self.assertEqual(screen.directory, self.root/'folder')
            self.assertEqual(screen.selected, [])
            screen.query_one('#file-up',TButton).press()
            await pilot.pause(); await self.settled(screen)
            rows.focus(); rows.highlighted = 0
            await pilot.press('enter'); await pilot.pause(); await self.settled(screen)
            self.assertEqual(screen.directory, self.root/'folder')
            self.assertEqual(screen.selected, [])

    async def test_directory_path_enter_up_and_error(self):
        app = self.app(OpenDirectory)
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            self.assertTrue(all(d for p,d in screen.entries))
            field=screen.query_one('#file-path',Input);field.value=str(self.root/'missing');field.focus()
            await pilot.press('enter');await pilot.pause();await self.settled(screen)
            self.assertNotEqual(str(screen.query_one('#file-status',Static).render()),'')
            field.value=str(self.root/'folder');await pilot.press('enter');await pilot.pause();await self.settled(screen)
            self.assertEqual(screen.directory,self.root/'folder')
            screen.query_one('#file-up',TButton).press();await pilot.pause();await self.settled(screen)
            self.assertEqual(screen.directory,self.root)
            screen.query_one('#file-confirm',TButton).press();await pilot.pause()
            self.assertEqual(app.result,str(self.root))
    async def test_save_new_overwrite_and_cancel(self):
        app = self.app(SaveFile, default='new.txt')
        async with app.ui.run_test(size=(90,35)) as pilot:
            screen = await self.open(app)
            self.assertEqual(screen.query_one('#file-name',Input).value,'new.txt')
            screen.query_one('#file-confirm',TButton).press();await pilot.pause()
            self.assertEqual(app.result,str(self.root/'new.txt'));self.assertFalse((self.root/'new.txt').exists())
            app.arguments['default']='a.txt';screen=await self.open(app)
            screen.query_one('#file-confirm',TButton).press();await pilot.pause();await self.settled(screen)
            self.assertEqual(str(screen.query_one('#file-confirm',TButton).label),'Replace')
            await pilot.press('escape');await pilot.pause();self.assertIsNone(app.result)
            screen=await self.open(app);screen.query_one('#file-confirm',TButton).press();await pilot.pause();await self.settled(screen)
            screen.query_one('#file-confirm',TButton).press();await pilot.pause()
            self.assertEqual(app.result,str(self.root/'a.txt'));self.assertEqual((self.root/'a.txt').read_text(),'a')
    async def test_slow_listing_keeps_ui_responsive_and_shutdown_releases(self):
        app = self.app(OpenFile)
        started = threading.Event()
        def slow(*args):
            started.set();time.sleep(.3);return _listing(*args)
        with patch('PUI.textual.file_dialog._listing',slow):
            async with app.ui.run_test(size=(45,18)) as pilot:
                app.children[0].children[0].children[0].ui.press()
                async def wait():
                    while not started.is_set(): await asyncio.sleep(.01)
                await asyncio.wait_for(wait(),3)
                app.ui.exit()
        self.assertIsNone(app.result)
        self.assertFalse(any(t.name.startswith('pui-textual-callback') for t in threading.enumerate()))
