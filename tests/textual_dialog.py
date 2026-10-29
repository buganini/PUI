"""Synchronous dialogs, serial callbacks and shutdown on the Textual pilot."""
import asyncio
import threading
import unittest
from PUI.textual import Application, Window, VBox, Button, Label, State, Information, Warning, Critical, Confirm, Prompt
from PUI.textual.dialog import MessageDialog
from textual.widgets import Input

class Example(Application):
    def setup(self):
        self.state=State()
        self.state.answer='idle'
        self.answers=[]
        self.threads=[]
    def content(self):
        with Window(), VBox():
            Button('Ask').click(self.ask)
            Button('Later').click(lambda e:self.answers.append('later'))
            Label(str(self.state.answer))
    def ask(self,event):
        self.threads.append(threading.get_ident())
        for helper in (Information,Warning,Critical):
            self.answers.append(helper('[plain] message',title='Test'))
        self.answers.append(Confirm('Continue?'))
        self.answers.append(Prompt('Value?',default='initial'))
        self.state.answer=repr(self.answers)

class DialogTests(unittest.IsolatedAsyncioTestCase):
    async def wait_dialog(self, app, kind):
        async def wait():
            while not isinstance(app.screen,MessageDialog) or app.screen.kind!=kind:
                await asyncio.sleep(.01)
        await asyncio.wait_for(wait(),3)

    async def test_sequence_empty_prompt_cancel_and_queue(self):
        app=Example()
        async with app.ui.run_test(size=(90,30)) as pilot:
            # PUI IDs are optional; invoke the native button just as the pilot does.
            app.children[0].children[0].children[0].ui.press()
            for kind in ('information','warning','critical'):
                await self.wait_dialog(app.ui,kind)
                if kind=='information':
                    app.children[0].children[0].children[1].ui.press()
                await pilot.press('escape');await pilot.pause()
            await self.wait_dialog(app.ui,'confirm')
            await pilot.press('escape');await pilot.pause()
            await self.wait_dialog(app.ui,'prompt')
            self.assertEqual(app.ui.screen.query_one(Input).value,'initial')
            app.ui.screen.query_one(Input).value=''
            await pilot.press('enter');await pilot.pause()
            self.assertEqual(app.answers,[None,None,None,False,'','later'])
            self.assertNotEqual(app.threads[0],threading.get_ident())
        self.assertFalse(any(t.name.startswith('pui-textual-callback') for t in threading.enumerate()))

    async def test_poster_confirm_and_prompt_cancellation(self):
        app=Example()
        async with app.ui.run_test() as pilot:
            poster=app.children[0].children[0].children[0].get_poster()
            def ask():
                app.answers.append(Confirm('Continue?'))
                app.answers.append(Prompt('Input'))
            poster(ask, delay=10)
            await self.wait_dialog(app.ui,'confirm')
            await pilot.pause()
            self.assertTrue(await pilot.click('#pui-dialog-ok'))
            await pilot.pause()
            await self.wait_dialog(app.ui,'prompt')
            await pilot.press('escape');await pilot.pause()
            self.assertEqual(app.answers,[True,None])

    async def test_shutdown_releases_pending_dialog(self):
        app=Example()
        async with app.ui.run_test() as pilot:
            app.children[0].children[0].children[0].ui.press()
            await self.wait_dialog(app.ui,'information')
            app.ui.exit()
        self.assertFalse(any(t.name.startswith('pui-textual-callback') for t in threading.enumerate()))

if __name__=='__main__':unittest.main()
