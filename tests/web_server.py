"""HTTP, binary IPC, real fork isolation, cookie ownership and TTL integration."""
import asyncio
import os
import unittest
from aiohttp import web, ClientSession, CookieJar, WSMsgType
from aiohttp.test_utils import TestServer
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

    async def test_default_all_hosts_keeps_origin_validation(self):
        from aiohttp import WSServerHandshakeError
        self.assertEqual(self.gateway.allow_hosts, {'*'})
        async with self.client.get(self.origin + '/pui/',
                headers={'Host': 'arbitrary.example'}) as response:
            self.assertEqual(response.status, 200)
        with self.assertRaises(WSServerHandshakeError) as raised:
            await self.client.ws_connect(self.origin + '/pui/pui/ws', protocols=[SUBPROTOCOL],
                headers={'Host': 'arbitrary.example', 'Origin': 'https://different.example'})
        self.assertEqual(raised.exception.status, 403)
        self.assertEqual(self.gateway.workers, {})

    async def test_explicit_hosts_apply_to_all_routes(self):
        gateway = Gateway('web_fixture:App', allow_hosts=['public.example', '[::1]'], base_url='/pui')
        async with TestServer(gateway.application()) as server:
            async with ClientSession() as client:
                for host in ('public.example', 'PUBLIC.EXAMPLE:443', 'public.example.', '[::1]:8866'):
                    async with client.get(server.make_url('/pui/'), headers={'Host': host}) as response:
                        self.assertEqual(response.status, 200, host)
                for path in ('/pui/', '/pui/pui/ws', '/pui/assets/' + gateway.build + '/client.js'):
                    for host in ('other.example', 'sub.public.example'):
                        async with client.get(server.make_url(path), headers={
                                'Host': host, 'X-Forwarded-Host': 'public.example'}) as response:
                            self.assertEqual(response.status, 403, (path, host))
                for host in ('public.example@other.example', 'public.example/path', '[::1]bad',
                             'public.example..', 'public.example:bad'):
                    async with client.get(server.make_url('/pui/'), headers={'Host': host}) as response:
                        self.assertEqual(response.status, 400, host)
        self.assertEqual(gateway.workers, {})

    async def test_empty_host_list_denies_requests(self):
        gateway = Gateway('web_fixture:App', allow_hosts=[])
        async with TestServer(gateway.application()) as server:
            async with ClientSession() as client:
                async with client.get(server.make_url('/')) as response:
                    self.assertEqual(response.status, 403)

    async def test_https_public_origin_on_http_upstream(self):
        from aiohttp import WSServerHandshakeError
        gateway = Gateway('web_fixture:App', base_url='https://public.example/pui')
        async with TestServer(gateway.application()) as server:
            # Model the browser's Secure cookie being forwarded by a TLS proxy
            # onto its HTTP upstream, without trusting forwarded headers.
            jar = CookieJar(unsafe=True, treat_as_secure_origin=server.make_url('/'))
            async with ClientSession(cookie_jar=jar) as client:
                async with client.get(server.make_url('/pui/')) as response:
                    self.assertTrue(response.cookies['pui_owner']['secure'])
                    html = await response.text()
                    self.assertIn('data-ws="wss://public.example/pui/pui/ws"', html)
                    self.assertIn('https://public.example/pui/assets/', html)
                endpoint = server.make_url('/pui/pui/ws')
                for origin in ('http://public.example', 'https://other.example'):
                    with self.assertRaises(WSServerHandshakeError) as raised:
                        await client.ws_connect(endpoint, protocols=[SUBPROTOCOL],
                            headers={'Origin': origin, 'X-Forwarded-Proto': 'https',
                                     'X-Forwarded-Host': 'other.example'})
                    self.assertEqual(raised.exception.status, 403)
                self.assertEqual(gateway.workers, {})
                async with client.ws_connect(endpoint, protocols=[SUBPROTOCOL],
                        headers={'Origin': 'https://public.example'}, compress=0) as ws:
                    await ws.send_bytes(self.codec.encode({
                        'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                        'body': {'client_build': gateway.build, 'capabilities': [
                            'render.snapshot', 'render.patch', 'binding.object_id'],
                            'viewport': {'width': 1000, 'height': 700, 'dpr': 1},
                            'resume_id': None}}))
                    self.assertEqual((await self.read(ws))['type'], 'ready')
                    self.assertEqual((await self.read(ws))['type'], 'render')
        self.assertEqual(gateway.workers, {})

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
