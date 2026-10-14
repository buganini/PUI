"""HTTP, binary IPC, real fork isolation, cookie ownership and TTL integration."""
import asyncio
import os
import unittest
from aiohttp import web, ClientSession, CookieJar, WSMsgType
from PUI.web.server import Gateway
from PUI.web.protocol import Codec, SUBPROTOCOL


class ServerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.gateway = Gateway('web_fixture:App', base_url='/pui', session_ttl=.15)
        self.runner = web.AppRunner(self.gateway.application(), shutdown_timeout=.2)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, '127.0.0.1', 0)
        await self.site.start()
        self.origin = 'http://127.0.0.1:' + str(self.site._server.sockets[0].getsockname()[1])
        self.client = ClientSession(cookie_jar=CookieJar(unsafe=True))
        self.codec = Codec()
        async with self.client.get(self.origin + '/pui/') as response:
            self.assertEqual(response.status, 200)
        self.sockets = []

    async def asyncTearDown(self):
        for ws in self.sockets:
            await ws.close()
        await self.client.close()
        await self.runner.cleanup()
        self.assertEqual(self.gateway.workers, {})

    async def connect(self, *, resume_id=None, client=None):
        ws = await (client or self.client).ws_connect(self.origin + '/pui/pui/ws',
            protocols=[SUBPROTOCOL], headers={'Origin': self.origin}, compress=0)
        self.sockets.append(ws)
        await ws.send_bytes(self.codec.encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
            'body': {'client_build': self.gateway.build, 'capabilities': [
                'render.snapshot', 'render.patch', 'binding.object_id'],
                'viewport': {'width': 1000, 'height': 700, 'dpr': 1}, 'resume_id': resume_id}}))
        return ws

    async def read(self, ws):
        message = await asyncio.wait_for(ws.receive(), 10)
        self.assertEqual(message.type, WSMsgType.BINARY, message)
        return self.codec.decode(message.data)

    async def send(self, ws, epoch, seq, kind, body):
        await ws.send_bytes(self.codec.encode({'v': 1, 'type': kind, 'session': epoch, 'seq': seq, 'body': body}))

    def nodes(self, render):
        def walk(node):
            yield node
            for child in node['children']:
                yield from walk(child)
        return list(walk(render['body']['roots'][0]))

    async def test_prefix_assets_and_no_workers_for_http(self):
        async with self.client.get(self.origin + '/pui', allow_redirects=False) as r:
            self.assertEqual(r.status, 308)
            self.assertEqual(r.headers['Location'], '/pui/')
        for name in ('client.js', 'client.css', 'zstd.wasm', 'THIRD_PARTY_LICENSES.txt'):
            async with self.client.get(self.origin + '/pui/assets/' + self.gateway.build + '/' + name) as r:
                self.assertEqual(r.status, 200)
                self.assertTrue(await r.read())
        self.assertEqual(len(self.gateway.sessions), 0)
        self.assertEqual(self.gateway.workers, {})

    async def test_fork_isolation_resume_and_no_event_replay(self):
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        epoch, resume_id = ready['session'], ready['body']['resume_id']
        first = self.gateway.workers[resume_id].process.pid
        self.assertNotEqual(first, os.getpid())
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, epoch, 2, 'ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        await self.send(ws, epoch, 3, 'event', {'node_id': button['id'], 'event': 'click',
            'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        patch = await self.read(ws)
        self.assertIn('count=1', str(patch))
        await ws.close()
        await asyncio.sleep(.02)
        resumed = await self.connect(resume_id=resume_id)
        again, restored = await self.read(resumed), await self.read(resumed)
        self.assertTrue(again['body']['resumed'])
        self.assertNotEqual(again['session'], epoch)
        self.assertIn('count=1', str(restored))
        self.assertEqual(self.gateway.workers[resume_id].process.pid, first)
        other = await self.connect()
        other_ready, other_tree = await self.read(other), await self.read(other)
        self.assertIn('count=0', str(other_tree))
        self.assertNotEqual(self.gateway.workers[other_ready['body']['resume_id']].process.pid, first)

    async def test_expired_worker_reaped_and_foreign_cookie_rejected(self):
        ws = await self.connect()
        ready = await self.read(ws)
        await self.read(ws)
        resume_id = ready['body']['resume_id']
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as foreign:
            async with foreign.get(self.origin + '/pui/'):
                pass
            stolen = await self.connect(resume_id=resume_id, client=foreign)
            self.assertEqual((await asyncio.wait_for(stolen.receive(), 5)).type, WSMsgType.CLOSE)
            self.assertIn(resume_id, self.gateway.workers)
        await ws.close()
        for _ in range(100):
            if resume_id not in self.gateway.workers:
                break
            await asyncio.sleep(.02)
        self.assertNotIn(resume_id, self.gateway.workers)
        new = await self.connect(resume_id=resume_id)
        self.assertFalse((await self.read(new))['body']['resumed'])
        await self.read(new)

    async def test_wrong_origin_rejected_before_worker_allocation(self):
        from aiohttp import WSServerHandshakeError
        with self.assertRaises(WSServerHandshakeError):
            await self.client.ws_connect(self.origin + '/pui/pui/ws', protocols=[SUBPROTOCOL],
                                         headers={'Origin': 'https://other.example'})
        self.assertEqual(len(self.gateway.sessions), 0)

    async def test_disconnect_during_output_keeps_worker_until_ttl(self):
        self.gateway.sessions.session_ttl = 10
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        resume_id = ready['body']['resume_id']
        pid = self.gateway.workers[resume_id].process.pid
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, ready['session'], 2, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        await self.send(ws, ready['session'], 3, 'event', {'node_id': button['id'],
            'event': 'click', 'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})
        await ws.close()
        await asyncio.sleep(.05)
        resumed = await self.connect(resume_id=resume_id)
        self.assertTrue((await self.read(resumed))['body']['resumed'])
        await self.read(resumed)
        self.assertEqual(self.gateway.workers[resume_id].process.pid, pid)
