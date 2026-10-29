"""SaveFile over real IPC in isolated and passthru modes."""
from pathlib import Path
import tempfile
import unittest
import web_dialog


class SaveFileTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = web_dialog.DialogTests.asyncTearDown
    connect = web_dialog.DialogTests.connect
    read = web_dialog.DialogTests.read
    send = web_dialog.DialogTests.send
    nodes = web_dialog.DialogTests.nodes
    disconnect = web_dialog.DialogTests.disconnect
    transmit = web_dialog.DialogTests.transmit
    click = web_dialog.DialogTests.click
    reply = web_dialog.DialogTests.reply
    passthru = False

    async def asyncSetUp(self):
        from functools import partial
        from unittest.mock import patch
        from PUI.web.server import Gateway
        import web_server
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'folder').mkdir()
        with patch('web_server.Gateway', partial(Gateway, passthru=self.passthru, webroot=self.root)):
            await web_dialog.DialogTests.asyncSetUp(self)
        self.gateway.factory = 'web_savefile_fixture:App'

    async def begin(self):
        ws = await self.connect()
        ready, render = await self.read(ws), await self.read(ws)
        self.epoch, self.sequence = ready['session'], 1
        await self.transmit(ws, 'ack', dict(render_rev=1, applied_rev=1, status='applied'))
        await self.click(ws, next(n for n in self.nodes(render) if n['type'] == 'Button'))
        dialog = await self.read(ws)
        self.assertEqual(dialog['body']['options']['stage'], 'choice')
        return ws, ready, dialog

    async def answer(self, ws, dialog, action, value=''):
        await self.reply(ws, dialog, dict(action=action, value=value))
        return await self.read(ws)

    async def test_download_and_session_cleanup(self):
        ws, ready, dialog = await self.begin()
        dialog = await self.answer(ws, dialog, 'download')
        self.assertEqual(dialog['body']['options']['stage'], 'name')
        result = await self.answer(ws, dialog, 'confirm', 'hello.txt')
        self.assertEqual(result['body']['status'], 'processed')
        render = await self.read(ws)
        worker = self.gateway.workers[ready['body']['resume_id']]
        paths = list(worker.downloads.root.glob('*/hello.txt'))
        # Selection allocates a directory, not a file.
        self.assertEqual(paths, [])
        directories = list(worker.downloads.root.iterdir())
        self.assertEqual(len(directories), 1)
        self.assertIn(str(directories[0] / 'hello.txt'), str(render))
        await self.gateway._stop(ready['body']['resume_id'], reason=b'Test complete')
        self.assertFalse(worker.downloads.root.exists())

    async def test_browse_cancel_and_http_remains_responsive(self):
        ws, _, dialog = await self.begin()
        dialog = await self.answer(ws, dialog, 'save')
        async with self.client.get(self.origin + '/pui/') as response:
            self.assertEqual(response.status, 200)
        self.assertIsNone(dialog['body']['options']['parent'])
        dialog = await self.answer(ws, dialog, 'browse', str(self.root / 'folder'))
        self.assertEqual(dialog['body']['options']['directory'], str(self.root / 'folder'))
        dialog = await self.answer(ws, dialog, 'browse', str(self.root.parent))
        self.assertIn('outside webroot', dialog['body']['options']['error'])
        await self.reply(ws, dialog, None)
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        self.assertIn('None', str(await self.read(ws)))

    async def test_shutdown_releases_pending_dialog(self):
        import asyncio
        import threading
        ws, ready, _ = await self.begin()
        await asyncio.wait_for(self.gateway._stop(ready['body']['resume_id'], reason=b'Test shutdown'), 5)
        self.assertFalse(self.gateway.workers)
        if self.passthru:
            self.assertFalse(any(t.name.startswith('pui-web-application') for t in threading.enumerate()))

    async def test_disconnect_returns_none(self):
        ws, ready, _ = await self.begin()
        await self.disconnect(ws)
        ws = await self.connect(resume_id=ready['body']['resume_id'])
        await self.read(ws)
        self.assertIn('None', str(await self.read(ws)))


class PassthruSaveFileTests(SaveFileTests):
    passthru = True
