import asyncio
from pathlib import Path
import unittest
from aiohttp import FormData, ClientSession, CookieJar
import web_server


class DropTests(unittest.IsolatedAsyncioTestCase):
    asyncTearDown = web_server.ServerTests.asyncTearDown
    connect = web_server.ServerTests.connect
    read = web_server.ServerTests.read
    send = web_server.ServerTests.send
    nodes = web_server.ServerTests.nodes
    disconnect = web_server.ServerTests.disconnect
    wait_until = web_server.ServerTests.wait_until

    async def asyncSetUp(self):
        await web_server.ServerTests.asyncSetUp(self)
        self.gateway.factory = 'web_drop_fixture:App'
        self.gateway.sessions.session_ttl = 0
        self.ws = await self.connect()
        self.ready = await self.read(self.ws)
        self.render = await self.read(self.ws)
        self.resume = self.ready['body']['resume_id']
        self.worker = self.gateway.workers[self.resume]
        self.seq = 1
        self.targets = {n['props']['text']: n for n in self.nodes(self.render) if n['type'] == 'Label' and 'drop' in n['events']}

    def headers(self, target='Accept'):
        node = self.targets[target]
        return {'Origin': self.origin, 'X-PUI-Upload': self.gateway._sign(self.worker.owner, 'upload'),
                'X-PUI-Session': self.resume, 'X-PUI-Epoch': self.ready['session'],
                'X-PUI-Node': node['id'], 'X-PUI-Target': node['events']['drop']}

    async def upload(self, files=(('a.txt', b'hello'),), *, target='Accept', headers=None, client=None):
        form = FormData()
        for name, data in files:
            form.add_field('files', data, filename=name, content_type='application/octet-stream')
        response = await (client or self.client).post(self.origin+'/pui/pui/upload', data=form,
                                                     headers=headers or self.headers(target))
        return response

    async def drop(self, key, target='Accept', token=None):
        n = self.targets[target]
        self.seq += 1
        await self.send(self.ws, self.ready['session'], self.seq, 'event', {
            'node_id': n['id'], 'event': 'drop', 'token': token or n['events']['drop'],
            'observed_render_rev': 1, 'data': {'upload_id': key, 'text': None, 'urls': [], 'x': 1, 'y': 2}})
        result = await self.read(self.ws)
        self.assertEqual(result['type'], 'result')
        result = await self.read(self.ws)
        self.assertEqual(result['type'], 'drop_result')
        return result['body']

    async def test_accept_reject_replay_and_worker_cleanup(self):
        response = await self.upload()
        self.assertEqual(response.status, 200, await response.text())
        key = (await response.json())['upload_id']
        folder = self.worker.uploads.directory(key)
        self.assertTrue((await self.drop(key))['accepted'])
        self.assertTrue(folder.exists())
        self.assertFalse((await self.drop(key))['accepted'])
        self.assertTrue(folder.exists(), 'Replay must not delete accepted files')
        for target in ('Reject', 'Implicit'):
            r = await self.upload(target=target)
            key = (await r.json())['upload_id']
            self.assertFalse((await self.drop(key, target))['accepted'])
            self.assertFalse(self.worker.uploads.directory(key).exists())
        root = self.worker.uploads.root
        await self.gateway._stop(self.resume)
        self.assertFalse(root.exists())

    async def test_extensions_limits_stale_and_other_owner(self):
        r = await self.upload((('valid.txt', b'hello'), ('bad.exe', b'bad')))
        self.assertEqual(r.status, 400)
        self.assertEqual(list(self.worker.uploads.root.iterdir()), [])
        self.worker.uploads.limits['max_file_bytes'] = 3
        r = await self.upload()
        self.assertEqual(r.status, 400)
        self.worker.uploads.limits['max_file_bytes'] = 64*1024**2
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as other:
            await other.get(self.origin+'/pui/')
            r = await self.upload(client=other)
            self.assertEqual(r.status, 403)
        r = await self.upload()
        key = (await r.json())['upload_id']
        self.assertFalse((await self.drop(key, token='old'))['accepted'])
        self.assertFalse(self.worker.uploads.directory(key).exists())

    async def test_quota_released_after_application_deletion(self):
        self.worker.uploads.limits['max_session_bytes'] = 5
        r = await self.upload()
        key = (await r.json())['upload_id']
        self.assertTrue((await self.drop(key))['accepted'])
        r = await self.upload()
        self.assertEqual(r.status, 400)
        for file in self.worker.uploads.directory(key).iterdir():
            file.unlink()
        r = await self.upload()
        self.assertEqual(r.status, 200)

    async def test_origin_token_and_batch_count(self):
        for field, value in [('Origin', 'https://other.invalid'), ('X-PUI-Upload', 'invalid')]:
            headers = self.headers()
            headers[field] = value
            response = await self.upload(headers=headers)
            self.assertEqual(response.status, 403)
        self.worker.uploads.limits['max_files'] = 1
        response = await self.upload((('a.txt', b'a'), ('b.txt', b'b')))
        self.assertEqual(response.status, 400)
        self.assertEqual(list(self.worker.uploads.root.iterdir()), [])

    async def test_crash_cleanup(self):
        response = await self.upload()
        key = (await response.json())['upload_id']
        self.assertTrue((await self.drop(key))['accepted'])
        root = self.worker.uploads.root
        self.worker.process.kill()
        await self.wait_until(lambda: not root.exists())
