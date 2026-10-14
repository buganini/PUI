"""HTTP, binary IPC, real fork isolation, cookie ownership and TTL integration."""
import asyncio
import os
import base64
import socket
import struct
from pathlib import Path
import unittest
from unittest.mock import patch
from aiohttp import web, ClientSession, CookieJar, WSMsgType
from aiohttp.test_utils import TestServer
from PUI.web.server import Gateway
from PUI.web.protocol import Codec, SUBPROTOCOL
from web_fixture import block_markers


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

    async def connect(self, *, resume_id=None, client=None, hello_changes=None):
        ws = await (client or self.client).ws_connect(self.origin + '/pui/pui/ws',
            protocols=[SUBPROTOCOL], headers={'Origin': self.origin}, compress=0)
        self.sockets.append(ws)
        body = {'client_build': self.gateway.build, 'capabilities': [
                'render.snapshot', 'render.patch', 'binding.object_id'],
                'viewport': {'width': 1000, 'height': 700, 'dpr': 1}, 'resume_id': resume_id}
        body.update(hello_changes or {})
        await ws.send_bytes(self.codec.encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                                             'body': body}))
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

    async def wait_until(self, condition, timeout=5):
        async def wait():
            while not condition():
                await asyncio.sleep(.01)
        await asyncio.wait_for(wait(), timeout)

    async def click_increment(self, ws, ready, snapshot):
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, ready['session'], 2, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        await self.send(ws, ready['session'], 3, 'event', {'node_id': button['id'],
            'event': 'click', 'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})

    async def test_crashed_worker_is_reaped_and_other_client_survives(self):
        healthy = await self.connect()
        healthy_ready, healthy_tree = await self.read(healthy), await self.read(healthy)
        self.gateway.factory = 'web_fixture:CrashApp'
        doomed = await self.connect()
        ready, tree = await self.read(doomed), await self.read(doomed)
        resume_id = ready['body']['resume_id']
        pid = self.gateway.workers[resume_id].process.pid
        await self.click_increment(doomed, ready, tree)
        self.assertEqual((await asyncio.wait_for(doomed.receive(), 5)).type, WSMsgType.CLOSE)
        await self.wait_until(lambda: resume_id not in self.gateway.workers)
        self.assertFalse(Path('/proc/' + str(pid)).exists())
        await self.click_increment(healthy, healthy_ready, healthy_tree)
        self.assertEqual((await self.read(healthy))['body']['status'], 'processed')
        self.assertIn('count=1', str(await self.read(healthy)))

    async def test_shutdown_reaps_blocked_callback_and_escalates_to_kill(self):
        self.gateway.factory = 'web_fixture:BlockedApp'
        ws = await self.connect()
        ready, tree = await self.read(ws), await self.read(ws)
        pid = self.gateway.workers[ready['body']['resume_id']].process.pid
        try:
            await self.click_increment(ws, ready, tree)
            await self.wait_until(lambda: bool(block_markers(pid)))
            await self.send(ws, ready['session'], 4, 'event', {'node_id': 'unused',
                'event': 'click', 'token': 'unused', 'observed_render_rev': 1,
                'data': {'padding': os.urandom(1024 * 1024)}})
            worker = self.gateway.workers[ready['body']['resume_id']]
            await self.wait_until(lambda: worker.writer.transport.get_write_buffer_size() > 0)
            self.gateway.factory = 'web_fixture:App'
            other = await self.connect()
            other_ready, other_tree = await self.read(other), await self.read(other)
            await self.click_increment(other, other_ready, other_tree)
            self.assertEqual((await self.read(other))['body']['status'], 'processed')
            self.assertIn('count=1', str(await self.read(other)))
            await asyncio.wait_for(self.runner.cleanup(), 5)
            self.assertEqual(self.gateway.workers, {})
            self.assertFalse(Path('/proc/' + str(pid)).exists())
        finally:
            for marker in block_markers(pid):
                marker.unlink()

    async def test_cancelled_ipc_startup_reaps_unregistered_child(self):
        session = self.gateway.sessions.create('test-owner')
        opening = asyncio.Event()
        created = []
        create_process = self.gateway.context.Process
        def capture_process(*args, **kwargs):
            process = create_process(*args, **kwargs)
            created.append(process)
            return process
        async def stalled_connection(*args, **kwargs):
            opening.set()
            await asyncio.Future()
        with patch.object(self.gateway.context, 'Process', side_effect=capture_process), \
                patch('PUI.web.server.asyncio.open_connection', side_effect=stalled_connection):
            startup = asyncio.create_task(self.gateway._spawn(session))
            await asyncio.wait_for(opening.wait(), 5)
            pid = created[0].pid
            startup.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await startup
        self.assertFalse(Path('/proc/' + str(pid)).exists())
        self.assertEqual(len(self.gateway.sessions), 0)
        self.assertEqual(self.gateway.workers, {})
        self.assertEqual(self.gateway.reapers, set())

    async def test_startup_timeout_reaps_child_and_releases_capacity(self):
        self.gateway.factory = 'web_fixture:SlowStartup'
        with patch('PUI.web.server.WORKER_START_TIMEOUT', .5):
            ws = await self.connect()
            await self.wait_until(lambda: bool(self.gateway.workers))
            pid = next(iter(self.gateway.workers.values())).process.pid
            try:
                await self.wait_until(lambda: bool(block_markers(pid)))
                self.assertEqual((await asyncio.wait_for(ws.receive(), 5)).type, WSMsgType.CLOSE)
                await self.wait_until(lambda: not self.gateway.workers)
                self.assertFalse(Path('/proc/' + str(pid)).exists())
                self.assertEqual(len(self.gateway.sessions), 0)
            finally:
                for marker in block_markers(pid):
                    marker.unlink()
        self.gateway.factory = 'web_fixture:App'
        healthy = await self.connect()
        self.assertEqual((await self.read(healthy))['type'], 'ready')
        await self.read(healthy)

    async def test_constructor_failure_releases_capacity(self):
        self.gateway.factory = 'web_fixture:BrokenStartup'
        ws = await self.connect()
        self.assertEqual((await asyncio.wait_for(ws.receive(), 5)).type, WSMsgType.CLOSE)
        await self.wait_until(lambda: not self.gateway.workers)
        self.assertEqual(len(self.gateway.sessions), 0)

    async def test_retained_capacity_rejects_new_tab_but_allows_resume(self):
        self.gateway.sessions.max_sessions = 1
        self.gateway.sessions.session_ttl = 10
        ws = await self.connect()
        ready = await self.read(ws)
        await self.read(ws)
        resume_id = ready['body']['resume_id']
        await ws.close()
        await self.wait_until(lambda: self.gateway.workers[resume_id].websocket is None)
        rejected = await self.connect()
        message = await asyncio.wait_for(rejected.receive(), 5)
        self.assertEqual(message.type, WSMsgType.CLOSE)
        self.assertIn('capacity', message.extra)
        resumed = await self.connect(resume_id=resume_id)
        self.assertTrue((await self.read(resumed))['body']['resumed'])
        await self.read(resumed)

    async def test_repeated_zero_ttl_sessions_release_processes_and_descriptors(self):
        self.gateway.sessions.session_ttl = 0
        baseline = None
        for _ in range(6):
            ws = await self.connect()
            ready = await self.read(ws)
            await self.read(ws)
            pid = self.gateway.workers[ready['body']['resume_id']].process.pid
            await ws.close()
            await self.wait_until(lambda: not self.gateway.workers and not self.gateway.reapers)
            self.assertFalse(Path('/proc/' + str(pid)).exists())
            current = len(list(Path('/proc/self/fd').iterdir()))
            if baseline is None:
                baseline = current  # fork supervisor/runtime descriptors are now warm
            else:
                self.assertLessEqual(current, baseline + 1)

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

    async def test_invalid_hello_does_not_allocate_worker(self):
        for changes in ({'viewport': []}, {'capabilities': [{}]}, {'resume_id': 1}):
            with self.subTest(changes=changes):
                ws = await self.connect(hello_changes=changes)
                message = await asyncio.wait_for(ws.receive(), 5)
                self.assertEqual(message.type, WSMsgType.CLOSE)
                self.assertEqual(message.data, 1008)
                self.assertEqual(self.gateway.workers, {})

    async def test_invalid_action_does_not_break_next_action(self):
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        epoch = ready['session']
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, epoch, 2, 'ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        body = {'node_id': [], 'event': 'click', 'token': button['events']['click'],
                'observed_render_rev': 1, 'data': {}}
        await self.send(ws, epoch, 3, 'event', body)
        result, unchanged = await self.read(ws), await self.read(ws)
        self.assertEqual(result['body']['status'], 'invalid')
        self.assertEqual(unchanged['body']['ops'], [])
        self.assertEqual(unchanged['body']['processed_seq'], 3)
        body['node_id'] = button['id']
        await self.send(ws, epoch, 4, 'event', body)
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        await self.send(ws, epoch, 5, 'ack', {'render_rev': 2, 'applied_rev': 2, 'status': 'applied'})
        self.assertIn('count=1', str(await self.read(ws)))

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

    async def test_resumed_editor_restarts_sequences_but_still_deduplicates(self):
        self.gateway.factory = 'web_fixture:EditApp'
        self.gateway.sessions.session_ttl = 10
        for kind in ('event', 'binding_write'):
            with self.subTest(kind=kind):
                ws = await self.connect()
                ready, snapshot = await self.read(ws), await self.read(ws)
                resume_id = ready['body']['resume_id']
                pid = self.gateway.workers[resume_id].process.pid
                editor = next(n for n in self.nodes(snapshot) if n['type'] == 'TextField')
                attachment = editor['bindings']['model']
                for attempt in range(2):
                    # The same node, source and attachment survive reconnection.
                    current = next(n for n in self.nodes(snapshot) if n['type'] == 'TextField')
                    self.assertEqual(current['bindings']['model'], attachment)
                    epoch = ready['session']
                    await self.send(ws, epoch, 2, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
                    edit_seq, value = (7, '2.5') if attempt == 0 else (1, '3.5')
                    body = {'node_id': editor['id'], 'observed_render_rev': 1}
                    if kind == 'event':
                        body.update(event='input', token=current['events']['input'],
                                    data={'value': value, 'edit_seq': edit_seq, 'composing': False})
                    else:
                        body.update(role='model', phase='commit', ref=attachment['ref'],
                            slot_token=attachment['slot_token'], attachment_token=attachment['token'],
                            observed_value_rev=snapshot['body']['bindings'][0]['value_rev'],
                            edit_seq=edit_seq, value=value)
                    await self.send(ws, epoch, 3, kind, body)
                    self.assertEqual((await self.read(ws))['body']['status'], 'processed')
                    rendered = await self.read(ws)
                    self.assertIn('count=' + str(attempt + 1) if kind == 'event' else value,
                                  str(rendered))
                    await self.send(ws, epoch, 4, 'ack',
                        {'render_rev': 2, 'applied_rev': 2, 'status': 'applied'})
                    await self.send(ws, epoch, 5, kind, body)
                    self.assertEqual((await self.read(ws))['body']['status'], 'stale')
                    self.assertEqual((await self.read(ws))['body']['ops'], [])
                    await ws.close()
                    await self.wait_until(lambda: self.gateway.workers[resume_id].websocket is None)
                    if attempt == 0:
                        ws = await self.connect(resume_id=resume_id)
                        again, snapshot = await self.read(ws), await self.read(ws)
                        self.assertTrue(again['body']['resumed'])
                        self.assertNotEqual(again['session'], epoch)
                        self.assertEqual(self.gateway.workers[resume_id].process.pid, pid)
                        ready = again

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

    async def test_slow_browser_output_is_bounded_and_worker_can_resume(self):
        self.gateway.factory = 'web_fixture:LargeOutputApp'
        self.gateway.sessions.session_ttl = 10
        endpoint = self.site._server.sockets[0].getsockname()
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        sock.setblocking(False)
        await asyncio.get_running_loop().sock_connect(sock, endpoint)
        reader, writer = await asyncio.open_connection(sock=sock)
        cookie = next(iter(self.client.cookie_jar)).OutputString()
        key = base64.b64encode(os.urandom(16)).decode('ascii')
        writer.write(('GET /pui/pui/ws HTTP/1.1\r\nHost: %s\r\nOrigin: %s\r\n'
            'Upgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Version: 13\r\n'
            'Sec-WebSocket-Key: %s\r\nSec-WebSocket-Protocol: %s\r\nCookie: %s\r\n\r\n' %
            (self.origin.split('//')[1], self.origin, key, SUBPROTOCOL, cookie)).encode('ascii'))
        try:
            self.assertIn(b'101 Switching Protocols', await reader.readuntil(b'\r\n\r\n'))
            # Use public asyncio transport control to model a browser that has
            # stopped reading; the small TCP window forces actual send pressure.
            writer.transport.pause_reading()
            payload = self.codec.encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
                'body': {'client_build': self.gateway.build,
                         'capabilities': ['render.snapshot', 'render.patch', 'binding.object_id'],
                         'viewport': {'width': 1000, 'height': 700, 'dpr': 1}, 'resume_id': None}})
            mask = os.urandom(4)
            prefix = bytes((0x82, 0x80 | len(payload))) if len(payload) < 126 else b'\x82\xfe' + struct.pack('!H', len(payload))
            with patch('PUI.web.server.WEBSOCKET_SEND_TIMEOUT', .05), self.assertLogs('PUI.web.server', level='WARNING') as logs:
                writer.write(prefix + mask + bytes(v ^ mask[i % 4] for i, v in enumerate(payload)))
                await writer.drain()
                await self.wait_until(lambda: bool(self.gateway.workers))
                resume_id, worker = next(iter(self.gateway.workers.items()))
                pid = worker.process.pid
                worker.transport.get_extra_info('socket').setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
                await self.wait_until(lambda: worker.websocket is None)
            self.assertIn('output queue did not drain', str(logs.output))
            self.assertTrue(Path('/proc/' + str(pid)).exists())
            resumed = await self.connect(resume_id=resume_id)
            ready, frame = await self.read(resumed), await self.read(resumed)
            self.assertTrue(ready['body']['resumed'])
            self.assertEqual(frame['type'], 'render')
            self.assertEqual(self.gateway.workers[resume_id].process.pid, pid)
        finally:
            writer.transport.abort()

    async def test_lost_ack_retries_immutable_render_then_retains_worker(self):
        self.gateway.factory = 'web_fixture:AckTimeoutApp'
        self.gateway.sessions.session_ttl = 10
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        resume_id, epoch = ready['body']['resume_id'], ready['session']
        pid = self.gateway.workers[resume_id].process.pid
        # Change State while the initial render still occupies the only credit.
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, epoch, 2, 'event', {'node_id': button['id'],
            'event': 'click', 'token': button['events']['click'], 'observed_render_rev': 1, 'data': {}})
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        for seq in (4, 5):
            retry = await self.read(ws)
            self.assertEqual(retry['seq'], seq)
            self.assertEqual(retry['body'], snapshot['body'])
        closed = await asyncio.wait_for(ws.receive(), 5)
        self.assertEqual(closed.type, WSMsgType.CLOSE)
        self.assertEqual(closed.data, 1013)
        self.assertIn('acknowledgement timeout', closed.extra)
        await self.wait_until(lambda: self.gateway.workers[resume_id].websocket is None)
        resumed = await self.connect(resume_id=resume_id)
        again, restored = await self.read(resumed), await self.read(resumed)
        self.assertTrue(again['body']['resumed'])
        self.assertEqual(self.gateway.workers[resume_id].process.pid, pid)
        self.assertIn('count=1', str(restored))
        self.assertNotEqual(again['session'], epoch)
        await self.send(resumed, again['session'], 2, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        # Successful ACK clears the deadline; duplicate ACK cannot re-arm it.
        await self.send(resumed, again['session'], 3, 'ack',
                        {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(resumed.receive(), .4)

    async def test_retried_ack_releases_one_credit_for_latest_state(self):
        self.gateway.factory = 'web_fixture:AckTimeoutApp'
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        retry = await self.read(ws)
        self.assertEqual(snapshot['body'], retry['body'])
        await self.click_increment(ws, ready, snapshot)
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        patch = await self.read(ws)
        self.assertEqual(patch['body']['mode'], 'patch')
        self.assertEqual(patch['body']['base_rev'], 1)
        self.assertEqual(patch['body']['rev'], 2)
        self.assertIn('count=1', str(patch))
        await self.send(ws, ready['session'], 4, 'ack',
                        {'render_rev': 2, 'applied_rev': 2, 'status': 'applied'})

    async def test_canvas_presentation_credit_does_not_block_dom_updates(self):
        self.gateway.factory = 'web_fixture:CanvasApp'
        ws = await self.connect()
        ready, snapshot = await self.read(ws), await self.read(ws)
        epoch = ready['session']
        self.assertEqual(snapshot['body']['canvases'], [])
        node = next(n for n in self.nodes(snapshot) if n['type'] == 'Canvas')
        button = next(n for n in self.nodes(snapshot) if n['type'] == 'Button')
        await self.send(ws, epoch, 2, 'ack', {'render_rev': 1, 'applied_rev': 1, 'status': 'applied'})
        await self.send(ws, epoch, 3, 'measure', {'node_id': node['id'], 'measure_rev': 1,
            'width': 200, 'height': 100, 'dpr': 2, 'visible': True})
        render = await self.read(ws)
        frame = next(op['frame'] for op in render['body']['ops'] if op['op'] == 'put_canvas')
        self.assertEqual(frame['frame_rev'], 1)
        await self.send(ws, epoch, 4, 'ack', {'render_rev': 2, 'applied_rev': 2, 'status': 'applied'})
        await self.send(ws, epoch, 5, 'event', {'node_id': button['id'], 'event': 'click',
            'token': button['events']['click'], 'observed_render_rev': 2, 'data': {}})
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        changed = await self.read(ws)
        self.assertIn('count=1', str(changed))
        self.assertNotIn('put_canvas', str(changed))
        await self.send(ws, epoch, 6, 'canvas_ack', {'node_id': node['id'], 'measure_rev': 1,
            'frame_rev': 1, 'status': 'drawn'})
        await self.send(ws, epoch, 7, 'ack', {'render_rev': 3, 'applied_rev': 3, 'status': 'applied'})
        next_frame = await self.read(ws)
        frame = next(op['frame'] for op in next_frame['body']['ops'] if op['op'] == 'put_canvas')
        self.assertEqual(frame['frame_rev'], 2)
        self.assertEqual(frame['commands'][0]['fill'], '#000002')
        await self.send(ws, epoch, 8, 'canvas_ack', {'node_id': node['id'], 'measure_rev': 1,
            'frame_rev': 1, 'status': 'drawn'})
        await self.send(ws, epoch, 9, 'ack', {'render_rev': 4, 'applied_rev': 4, 'status': 'applied'})
        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(ws.receive(), .05)
        await self.send(ws, epoch, 10, 'event', {'node_id': node['id'], 'event': 'mousedown',
            'token': node['events']['mousedown'], 'observed_render_rev': 4,
            'data': {'x': 1, 'y': 2, 'button': 1, 'buttons': 1, 'modifiers': 0,
                     'pointer_id': 3, 'cancelled': False}})
        self.assertEqual((await self.read(ws))['body']['status'], 'processed')
        self.assertIn('count=2', str(await self.read(ws)))
