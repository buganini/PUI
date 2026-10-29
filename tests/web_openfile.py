"""File selection and scoped HTTP uploads through real worker IPC."""
import unittest
import asyncio
from pathlib import Path
from aiohttp import FormData
import web_savefile

class OpenFileTests(unittest.IsolatedAsyncioTestCase):
    passthru = False
    asyncTearDown = web_savefile.SaveFileTests.asyncTearDown
    connect = web_savefile.SaveFileTests.connect
    read = web_savefile.SaveFileTests.read
    send = web_savefile.SaveFileTests.send
    nodes = web_savefile.SaveFileTests.nodes
    disconnect = web_savefile.SaveFileTests.disconnect
    transmit = web_savefile.SaveFileTests.transmit
    click = web_savefile.SaveFileTests.click
    reply = web_savefile.SaveFileTests.reply
    answer = web_savefile.SaveFileTests.answer
    test_disconnect_returns_none = web_savefile.SaveFileTests.test_disconnect_returns_none
    test_shutdown_releases_pending_dialog = web_savefile.SaveFileTests.test_shutdown_releases_pending_dialog
    async def asyncSetUp(self):
        await web_savefile.SaveFileTests.asyncSetUp(self)
        self.gateway.factory = 'web_openfile_fixture:App'
        (self.root / 'a.txt').write_text('a')
        (self.root / 'b.txt').write_text('b')

    async def begin(self, name='Open File'):
        ws = await self.connect()
        ready, render = await self.read(ws), await self.read(ws)
        self.epoch, self.sequence = ready['session'], 1
        await self.transmit(ws, 'ack', dict(render_rev=1, applied_rev=1, status='applied'))
        await self.click(ws, next(n for n in self.nodes(render) if n['type']=='Button' and n['props']['text']==name))
        dialog = await self.read(ws)
        self.assertEqual(dialog['body']['kind'], 'openfile')
        return ws, ready, dialog

    async def upload(self, ready, dialog, names, token=None):
        worker = self.gateway.workers[ready['body']['resume_id']]
        form = FormData(quote_fields=False)
        for name in names:
            form.add_field('files', b'hello', filename=name, content_type='application/octet-stream')
        return await self.client.post(self.origin+'/pui/pui/upload', data=form, headers={
            'Origin': self.origin, 'X-PUI-Upload': self.gateway._sign(worker.owner,'upload'),
            'X-PUI-Session':ready['body']['resume_id'], 'X-PUI-Epoch':self.epoch,
            'X-PUI-Dialog':token or dialog['body']['options']['token']})

    async def test_server_file_and_multiple(self):
        ws, ready, dialog = await self.begin('Open Files')
        result = await self.answer(ws, dialog, 'open', [str(self.root/'a.txt'), str(self.root/'b.txt')])
        self.assertEqual(result['body']['status'], 'processed')
        render = str(await self.read(ws))
        self.assertIn('a.txt', render); self.assertIn('b.txt', render)

    async def test_directory_upload_preserves_tree(self):
        ws, ready, dialog = await self.begin('Open Directory')
        async with await self.upload(ready, dialog, ['data/a.txt','data/sub/b.txt']) as response:
            self.assertEqual(response.status, 200, await response.text())
            key = (await response.json())['upload_id']
        await self.answer(ws, dialog, 'upload', key)
        await self.read(ws)
        worker = self.gateway.workers[ready['body']['resume_id']]
        self.assertEqual((worker.uploads.directory(key)/'content/data/sub/b.txt').read_text(), 'hello')
        async with await self.upload(ready, dialog, ['data/x.txt']) as response:
            self.assertEqual(response.status, 409)

    async def test_cancel_discards_completed_upload(self):
        ws, ready, dialog = await self.begin()
        async with await self.upload(ready, dialog, ['a.txt']) as response:
            key = (await response.json())['upload_id']
        await self.reply(ws, dialog, None)
        await self.read(ws); await self.read(ws)
        worker = self.gateway.workers[ready['body']['resume_id']]
        self.assertFalse(worker.uploads.directory(key).exists())

    async def test_cancel_during_stream_removes_partial_files(self):
        ws, ready, dialog = await self.begin()
        worker = self.gateway.workers[ready['body']['resume_id']]
        release = asyncio.Event()
        async def chunks():
            yield b'x' * (128 * 1024)
            await release.wait()
            yield b'end'
        form = FormData()
        form.add_field('files', chunks(), filename='large.txt', content_type='application/octet-stream')
        request = asyncio.create_task(self.client.post(self.origin+'/pui/pui/upload', data=form, headers={
            'Origin': self.origin, 'X-PUI-Upload': self.gateway._sign(worker.owner,'upload'),
            'X-PUI-Session':ready['body']['resume_id'], 'X-PUI-Epoch':self.epoch,
            'X-PUI-Dialog':dialog['body']['options']['token']}))
        try:
            async def receiving():
                while not any(p.stat().st_size for p in worker.uploads.root.glob('*/*.part')):
                    await asyncio.sleep(.01)
            await asyncio.wait_for(receiving(), 3)
            await self.reply(ws, dialog, None)
            await self.read(ws); await self.read(ws)
            self.assertEqual(list(worker.uploads.root.iterdir()), [])
        finally:
            release.set()
            async with await request as response:
                self.assertEqual(response.status, 409)

    async def test_invalid_token_and_paths(self):
        ws, ready, dialog = await self.begin('Open Directory')
        async with await self.upload(ready, dialog, ['data/x.txt'], token='wrong') as response:
            self.assertEqual(response.status, 409)
        async with await self.upload(ready, dialog, ['data/../x.txt']) as response:
            self.assertEqual(response.status, 400)
        await self.reply(ws, dialog, None)
        await self.read(ws); await self.read(ws)

class PassthruOpenFileTests(OpenFileTests):
    passthru = True
