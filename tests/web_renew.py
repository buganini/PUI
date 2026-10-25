"""Session renewal keeps authorization and unrelated workers, including TTL 0."""
import asyncio
import re
import unittest

from aiohttp import ClientSession, CookieJar, WSMsgType
from aiohttp.test_utils import TestServer

from PUI.web.protocol import Codec, StreamCodec, SUBPROTOCOL
from PUI.web.server import COOKIE, Gateway


class RenewTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.logins = []
        def auth(username, password):
            self.logins.append(username)
            return username == 'test' and password == 'test123'
        self.gateway = Gateway('web_fixture:App', mount_path='/pui', auth=auth, session_ttl=0)
        self.server = TestServer(self.gateway.application())
        await self.server.start_server()
        self.origin = str(self.server.make_url('/')).rstrip('/')
        self.client = ClientSession(cookie_jar=CookieJar(unsafe=True))
        self.sockets = []

    async def asyncTearDown(self):
        for ws in self.sockets:
            await ws.close()
        await self.client.close()
        await self.server.close()
        self.assertEqual(self.gateway.workers, {})

    async def entry(self, client=None):
        client = client or self.client
        async with client.get(self.server.make_url('/pui/')) as response:
            html = await response.text()
        if 'class="pui-login"' in html:
            fields = {'username': 'test', 'password': 'test123',
                      'csrf': re.search(r'name="csrf" value="([^"]+)"', html).group(1)}
            async with client.post(self.server.make_url('/pui/pui/login'), data=fields) as response:
                html = await response.text()
        self.assertIn('data-auth-required="%s"' % ('true' if self.gateway.auth else 'false'), html)
        self.assertIn('data-renew="/pui/pui/renew"', html)
        token = re.search(r'data-renew-token="([^"]+)"', html).group(1)
        self.assertNotEqual(token, re.search(r'data-logout-token="([^"]+)"', html).group(1))
        cookie = client.cookie_jar.filter_cookies(self.server.make_url('/pui/'))[COOKIE].value
        return cookie, token

    async def connect(self, client=None):
        ws = await (client or self.client).ws_connect(self.server.make_url('/pui/pui/ws'),
            protocols=[SUBPROTOCOL], headers={'Origin': self.origin})
        self.sockets.append(ws)
        await ws.send_bytes(Codec().encode({'v': 1, 'type': 'hello', 'session': None, 'seq': 1,
            'body': {'client_build': self.gateway.build, 'capabilities': [
                'render.snapshot', 'render.patch', 'binding.object_id'],
                'viewport': {'width': 100, 'height': 100, 'dpr': 1}, 'resume_id': None}}))
        decoder = StreamCodec()
        try:
            ready = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
            frame = decoder.decode((await asyncio.wait_for(ws.receive(), 5)).data)
            self.assertEqual(frame['type'], 'render')
        finally:
            decoder.close()
        return ws, ready['body']['resume_id']

    async def post(self, data, *, client=None, headers=None):
        return await (client or self.client).post(self.server.make_url('/pui/pui/renew'), data=data,
            headers={'Origin': self.origin} if headers is None else headers, allow_redirects=False)

    async def check_renew(self, *, authenticated, attached):
        if not authenticated:
            self.gateway.auth = None
        cookie, token = await self.entry()
        self.gateway.sessions.max_sessions = 2
        target, old_id = await self.connect()
        other, other_id = await self.connect()
        old_process = self.gateway.workers[old_id].process
        other_worker = self.gateway.workers[other_id]
        if not attached:
            await target.close()
            async def detached():
                while self.gateway.workers[old_id].websocket is not None:
                    await asyncio.sleep(.01)
            await asyncio.wait_for(detached(), 5)
        # Concurrent duplicate POSTs wait for the same reaper and release capacity.
        fields = {'csrf': token, 'resume_id': old_id}
        responses = await asyncio.gather(self.post(fields), self.post(fields))
        for response in responses:
            async with response:
                self.assertEqual(response.status, 303)
                self.assertEqual(response.headers['Location'], '../')
                self.assertNotIn(COOKIE, response.cookies)
        self.assertEqual(set(self.gateway.workers), {other_id})
        # Process.close() releases handles only after the worker has stopped.
        with self.assertRaises(ValueError):
            old_process.is_alive()
        self.assertIs(self.gateway.workers[other_id], other_worker)
        self.assertTrue(other_worker.process.is_alive())
        self.assertFalse(other.closed)
        if attached:
            closed = await asyncio.wait_for(target.receive(), 5)
            self.assertEqual((closed.type, closed.data), (WSMsgType.CLOSE, 4003))
        async with self.client.get(self.server.make_url('/pui/')) as response:
            self.assertIn('id="pui-root"', await response.text())
            self.assertEqual(response.cookies[COOKIE].value, cookie)
        self.assertEqual(self.logins, ['test'] if authenticated else [])
        _, new_id = await self.connect()
        self.assertNotEqual(new_id, old_id)
        self.assertEqual(len(self.gateway.workers), 2)
        # Replaying a completed renewal cannot destroy the replacement or other tab.
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 303)
        self.assertEqual(set(self.gateway.workers), {other_id, new_id})

    async def test_authenticated_retained_session_renewal_preserves_login(self):
        await self.check_renew(authenticated=True, attached=False)

    async def test_authenticated_active_session_renewal_closes_only_target(self):
        await self.check_renew(authenticated=True, attached=True)

    async def test_anonymous_session_renewal_preserves_owner(self):
        await self.check_renew(authenticated=False, attached=False)

    async def test_renew_rejects_invalid_forms_and_missing_owner(self):
        async with await self.post({'csrf': 'forged', 'resume_id': 'unknown'}) as response:
            self.assertEqual(response.status, 403)
        _, token = await self.entry()
        _, resume_id = await self.connect()
        fields = {'csrf': token, 'resume_id': resume_id}
        async with self.client.get(self.server.make_url('/pui/')) as response:
            logout_token = re.search(r'data-logout-token="([^"]+)"', await response.text()).group(1)
        for data, headers, status in (
            (dict(fields, csrf='forged'), {'Origin': self.origin}, 403),
            (dict(fields, csrf=logout_token), {'Origin': self.origin}, 403),
            (fields, {'Origin': 'https://other.example'}, 403),
            (fields, [('Origin', self.origin), ('Origin', self.origin)], 403),
            (list(fields.items()) * 2, {'Origin': self.origin}, 400),
            ({'csrf': token}, {'Origin': self.origin}, 400),
            (dict(fields, resume_id='x' * 2048), {'Origin': self.origin}, 413),
            ('{}', {'Origin': self.origin, 'Content-Type': 'application/json'}, 415),
        ):
            async with await self.post(data, headers=headers) as response:
                self.assertEqual(response.status, status)
            self.assertIn(resume_id, self.gateway.workers)
        async with self.client.get(self.server.make_url('/pui/pui/renew')) as response:
            self.assertEqual(response.status, 405)

    async def test_renew_cannot_remove_another_owners_worker(self):
        await self.entry()
        _, resume_id = await self.connect()
        async with ClientSession(cookie_jar=CookieJar(unsafe=True)) as foreign:
            _, token = await self.entry(foreign)
            async with await self.post({'csrf': token, 'resume_id': resume_id}, client=foreign) as response:
                self.assertEqual(response.status, 403)
        self.assertIn(resume_id, self.gateway.workers)
        self.assertTrue(self.gateway.workers[resume_id].process.is_alive())

    async def test_expired_session_renewal_is_harmless_and_revoked_cookie_is_rejected(self):
        cookie, token = await self.entry()
        fields = {'csrf': token, 'resume_id': 'expired'}
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 303)
        self.assertEqual(self.gateway.workers, {})
        self.gateway.owners.pop(cookie.split('.')[0])
        async with await self.post(fields) as response:
            self.assertEqual(response.status, 403)


if __name__ == '__main__':
    unittest.main()
